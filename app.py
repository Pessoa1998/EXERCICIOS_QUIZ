import streamlit as st
from datetime import datetime, timezone
import json
import os
import time
import threading

# ---------- Config ----------
st.set_page_config(page_title="Quiz Interativo", layout="centered")
BASE_DIR = os.path.dirname(__file__)
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.json")
STATE_FILE = os.path.join(BASE_DIR, "game_state.json")
LOCKFILE = STATE_FILE + ".lock"
INPROC_LOCK = threading.Lock()
QUESTION_DURATION = 20

LOCK_WAIT_TIMEOUT = 5.0
LOCK_POLL = 0.05
REPLACE_RETRIES = 20
REPLACE_DELAY = 0.05

# ---------- Lock helpers ----------
def _try_create_lockfile(lockfile):
    try:
        fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False

def acquire_lock(lockfile=LOCKFILE, timeout=LOCK_WAIT_TIMEOUT, poll=LOCK_POLL):
    start = time.time()
    while True:
        if _try_create_lockfile(lockfile):
            return True
        try:
            mtime = os.path.getmtime(lockfile)
            if time.time() - mtime > max(30.0, timeout * 3):
                os.remove(lockfile)
                continue
        except FileNotFoundError:
            continue
        if time.time() - start >= timeout:
            return False
        time.sleep(poll)

def release_lock(lockfile=LOCKFILE):
    try:
        if os.path.exists(lockfile):
            os.remove(lockfile)
    except Exception:
        pass

# ---------- Questions ----------
def load_questions():
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Arquivo de perguntas não encontrado.")
        st.stop()

# ---------- State ----------
def create_new_state():
    return {
        "players": {},
        "current_index": -1,
        "is_active": False,
        "is_ended": False,
        "time_remaining": QUESTION_DURATION,
        "question_start": None,
        "questions": load_questions(),
        "last_update": datetime.now(timezone.utc).isoformat()
    }

def load_state(wait_for_lock=True, lock_timeout=LOCK_WAIT_TIMEOUT):
    if not os.path.exists(STATE_FILE):
        return create_new_state()
    start = time.time()
    while True:
        if wait_for_lock and os.path.exists(LOCKFILE):
            if time.time() - start > lock_timeout:
                return create_new_state()
            time.sleep(LOCK_POLL)
            continue
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return create_new_state()

def save_state_atomic(state):
    pid = os.getpid()
    ts = int(time.time() * 1000)
    tmp_path = STATE_FILE + f".tmp.{pid}.{ts}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    for _ in range(REPLACE_RETRIES):
        try:
            os.replace(tmp_path, STATE_FILE)
            return
        except PermissionError:
            time.sleep(REPLACE_DELAY)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

def save_state(state):
    got = acquire_lock()
    if not got:
        try:
            save_state_atomic(state)
            return
        except Exception:
            return
    try:
        with INPROC_LOCK:
            save_state_atomic(state)
    finally:
        release_lock()

def safe_update_state(updater):
    got = acquire_lock()
    if not got:
        state = load_state(wait_for_lock=False)
        updater(state)
        state["last_update"] = datetime.now(timezone.utc).isoformat()
        save_state_atomic(state)
        return state
    try:
        with INPROC_LOCK:
            current = load_state(wait_for_lock=False)
            updater(current)
            current["last_update"] = datetime.now(timezone.utc).isoformat()
            save_state_atomic(current)
            return current
    finally:
        release_lock()

# ---------- Game logic ----------
def tick_time(state):
    if state.get("is_active") and state.get("question_start"):
        try:
            start = datetime.fromisoformat(state["question_start"])
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            remaining = max(0, int(QUESTION_DURATION - elapsed))
            state["time_remaining"] = remaining
            if remaining <= 0:
                end_question()
        except Exception:
            state["is_active"] = False
            state["time_remaining"] = 0
            state["question_start"] = None

def add_player(name):
    def updater(state):
        pid = f"p_{int(time.time()*1000)}_{len(state.get('players', {}))}"
        state.setdefault("players", {})[pid] = {"name": name, "score": 0, "answers": {}}
        st.session_state.player_id = pid
    return safe_update_state(updater)

def submit_answer(player_id, answer_index):
    state = load_state()
    idx = state.get("current_index", -1)
    if not (0 <= idx < len(state.get("questions", []))):
        return False, "Nenhuma pergunta ativa."
    if not state.get("is_active"):
        return False, "Pergunta não está ativa."
    q = state["questions"][idx]
    p = state.get("players", {}).get(player_id)
    if p is None:
        return False, "Jogador não encontrado."
    if q["id"] in p.get("answers", {}):
        return False, "Você já respondeu."

    def updater(state_inner):
        p_inner = state_inner["players"].get(player_id)
        if p_inner:
            p_inner["answers"][q["id"]] = answer_index
            # ✅ atualizar score na hora se acertou
            if answer_index == q.get("correta"):
                p_inner["score"] = p_inner.get("score", 0) + 1
    safe_update_state(updater)
    return True, "Resposta registrada."

def start_question(duration=QUESTION_DURATION):
    def updater(state):
        idx = state.get("current_index", -1)
        if 0 <= idx < len(state.get("questions", [])):
            state["is_active"] = True
            state["is_ended"] = False
            state["time_remaining"] = duration
            state["question_start"] = datetime.now(timezone.utc).isoformat()
    return safe_update_state(updater)

def end_question():
    def updater(state):
        state["is_active"] = False
        state["is_ended"] = True
        state["time_remaining"] = 0
        state["question_start"] = None
    return safe_update_state(updater)

def advance_question():
    def updater(state):
        if state.get("current_index", -1) < len(state.get("questions", [])) - 1:
            state["current_index"] = state.get("current_index", -1) + 1
            state["is_active"] = False
            state["is_ended"] = False
            state["time_remaining"] = QUESTION_DURATION
            state["question_start"] = None
        else:
            state["current_index"] = len(state.get("questions", []))
            state["is_active"] = False
            state["is_ended"] = False
    return safe_update_state(updater)

def get_ranking(state):
    return sorted(
        [{"name": p.get("name"), "score": p.get("score", 0)} for p in state.get("players", {}).values()],
        key=lambda x: x["score"], reverse=True
    )

# ---------- UI ----------
st.title("📖 Quiz Interativo")

role = st.selectbox("Escolha seu papel", ["Participante", "Moderador"], key="select_role")

if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

state = load_state(wait_for_lock=True)
tick_time(state)

# Moderador UI
if role == "Moderador":
    st.header("Painel do Moderador")
    cols = st.columns(4)
    if cols[0].button("🔼 Iniciar Jogo", key="mod_start_game"):
        safe_update_state(lambda s: s.update({"current_index": 0}))
        state = load_state(wait_for_lock=True)
    if cols[1].button("▶ Liberar Pergunta", key="mod_start_question"):
        start_question()
    if cols[2].button("⏸ Encerrar Pergunta", key="mod_end_question"):
        end_question()
    if cols[3].button("➡ Avançar Pergunta", key="mod_next_question"):
        advance_question()

    st.markdown("**Jogadores Conectados (placar atualizado)**")
    for i, p in enumerate(get_ranking(state), start=1):
        st.write(f"{i}. {p['name']} — {p['score']} pts")

    idx = state.get("current_index", -1)
    questions = state.get("questions", [])
    if 0 <= idx < len(questions):
        q = questions[idx]
        st.markdown(f"### 🎯 Tema: *{q.get('tema')}*")
        st.markdown(f"## {q.get('pergunta')}")
        if state.get("is_active"):
            progress_value = int((QUESTION_DURATION - state.get("time_remaining", QUESTION_DURATION)) / QUESTION_DURATION * 100)
            st.progress(progress_value)
            st.write(f"Tempo restante: {state.get('time_remaining', 0)}s")
        elif state.get("is_ended"):
            st.write("**Fim da pergunta — Explicação**")
            st.write("Resposta correta:", q.get("opcoes", [""])[q.get("correta", 0)])
            st.info(f"📖 Base bíblica: {q.get('base_biblica', '')}")

# Participante UI
else:
    st.header("Entrar como Participante")
    name = st.text_input("Nome / apelido", key="participant_name")

    if st.session_state.player_id is None:
        if st.button("Entrar no Quiz", key="enter_quiz"):
            if name.strip():
                add_player(name.strip())
                state = load_state(wait_for_lock=True)
            else:
                st.warning("Digite seu nome!")
    else:
        pid = st.session_state.player_id
        players = state.get("players", {})
        if isinstance(pid, str) and pid in players:
            st.info(f"Você está conectado como: {players[pid].get('name')}")
            idx = state.get("current_index", -1)
            questions = state.get("questions", [])
            if 0 <= idx < len(questions):
                q = questions[idx]
                st.markdown(f"### 🎯 Tema: *{q.get('tema')}*")
                st.markdown(f"## {q.get('pergunta')}")
                if state.get("is_active"):
                    progress_value = int((QUESTION_DURATION - state.get("time_remaining", QUESTION_DURATION)) / QUESTION_DURATION * 100)
                    st.progress(progress_value)
                    st.write(f"Tempo restante: {state.get('time_remaining', 0)}s")
                    already = q.get("id") in players[pid].get("answers", {})
                    for i, opt in enumerate(q.get("opcoes", [])):
                        btn_key = f"{pid}_{q.get('id')}_{i}"
                        if already:
                            chosen = players[pid]["answers"][q.get("id")]
                            st.button(f"{opt} {'✅' if chosen == i else ''}", key=btn_key, disabled=True)
                        else:
                            if st.button(opt, key=btn_key):
                                ok, msg = submit_answer(pid, i)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.warning(msg)
                elif state.get("is_ended"):
                    st.write("**Fim da pergunta — Explicação**")
                    st.write("Resposta correta:", q.get("opcoes", [""])[q.get("correta", 0)])
                    st.info(f"📖 Base bíblica: {q.get('base_biblica', '')}")
                    st.write("Aguardando o moderador avançar...")
            else:
                st.write("Ainda não há perguntas ativas. Aguarde o moderador.")
        else:
            st.warning("Seu ID não foi encontrado. Entre novamente.")
            st.session_state.player_id = None

# Auto-refresh
col1, col2 = st.columns([3, 1])
with col2:
    if st.session_state.auto_refresh:
        if st.button("Parar Auto-refresh", key="stop_refresh"):
            st.session_state.auto_refresh = False
    else:
        if st.button("Iniciar Auto-refresh (1s)", key="start_refresh"):
            st.session_state.auto_refresh = True

if st.session_state.auto_refresh:
    time.sleep(1)
    st.rerun()
