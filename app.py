import base64
import random
import chess
import chess.svg
import streamlit as st
from streamlit_clickable_images import clickable_images

# 1. Page Configuration
st.set_page_config(page_title="Chess Opening Trainer", layout="centered")

# 2. Comprehensive Opening Database with Variations
# Organized by Color -> Opening Name -> Variation Name -> Move List (UCI format)
OPENING_DATABASE = {
    "White": {
        "London System": {
            "Main Line (vs 2...Nf6)": [
                "d2d4",
                "g8f6",
                "c1f4",
                "d7d5",
                "e2e3",
                "e7e6",
                "g1f3",
            ],
            "Jabava Attack (vs 2...e6)": [
                "d2d4",
                "e7e6",
                "c1f4",
                "g8f6",
                "e2e3",
                "c7c5",
                "c2c3",
            ],
        },
        "Italian Game": {
            "Giuoco Piano": [
                "e2e4",
                "e7e5",
                "g1f3",
                "b8c6",
                "f1c4",
                "f8c5",
                "c2c3",
            ],
            "Two Knights Defense": [
                "e2e4",
                "e7e5",
                "g1f3",
                "b8c6",
                "f1c4",
                "g8f6",
                "d2d4",
            ],
        },
    },
    "Black": {
        "Caro-Kann Defense": {
            "Classical Variation": [
                "e2e4",
                "c7c6",
                "d2d4",
                "d7d5",
                "b1c3",
                "d5e4",
                "c3e4",
                "c8f5",
            ],
            "Advance Variation": [
                "e2e4",
                "c7c6",
                "d2d4",
                "d7d5",
                "e4e5",
                "c8f5",
                "g1f3",
            ],
        },
        "French Defense": {
            "Advance Variation": [
                "e2e4",
                "e7e6",
                "d2d4",
                "d7d5",
                "e4e5",
                "c7c5",
                "c2c3",
            ],
        },
    },
}

# 3. Initialize Session State
if "app_mode" not in st.session_state:
  st.session_state.app_mode = "menu"  # "menu" or "drilling"
if "current_drills" not in st.session_state:
  st.session_state.current_drills = []
if "drill_idx" not in st.session_state:
  st.session_state.drill_idx = 0
if "move_idx" not in st.session_state:
  st.session_state.move_idx = 0
if "board" not in st.session_state:
  st.session_state.board = chess.Board()
if "selected_sq" not in st.session_state:
  st.session_state.selected_sq = None
if "feedback" not in st.session_state:
  st.session_state.feedback = "Make your move."


def start_drill_session(drills_list):
  """Starts a sequence of drills (either a specific variation or randomized list)."""
  st.session_state.current_drills = drills_list
  st.session_state.drill_idx = 0
  st.session_state.app_mode = "drilling"
  load_current_drill()


def load_current_drill():
  """Loads the active drill card."""
  drill = st.session_state.current_drills[st.session_state.drill_idx]
  st.session_state.move_idx = 0
  st.session_state.board = chess.Board()
  st.session_state.selected_sq = None
  st.session_state.feedback = "Tap a piece to start."

  # If playing as Black, automatically push White's first move(s)
  while st.session_state.move_idx < len(drill["moves"]):
    if st.session_state.board.turn != drill["player_color"]:
      opp_move = drill["moves"][st.session_state.move_idx]
      st.session_state.board.push(chess.Move.from_uci(opp_move))
      st.session_state.move_idx += 1
    else:
      break


# ==========================================
# VIEW 1: THE MENU SCREEN
# ==========================================
if st.session_state.app_mode == "menu":
  st.title("🎯 Chess Opening Trainer")
  st.write("Select a repertoire category below to choose your opening drill:")

  # Collect all individual variations for a global "Shuffle All" option
  all_variations = []
  for color, openings in OPENING_DATABASE.items():
    p_color = chess.WHITE if color == "White" else chess.BLACK
    for op_name, variations in openings.items():
      for var_name, moves in variations.items():
        all_variations.append({
            "title": f"{color} - {op_name}: {var_name}",
            "player_color": p_color,
            "moves": moves,
        })

  if st.button("🔀 Shuffle All Drills (Randomize Everything)", use_container_width=True):
    shuffled = all_variations.copy()
    random.shuffle(shuffled)
    start_drill_session(shuffled)
    st.rerun()

  st.divider()

  # Tabs for White vs Black repertoires
  tab_white, tab_black = st.tabs(["White Repertoire", "Black Repertoire"])

  for tab, color_key in zip([tab_white, tab_black], ["White", "Black"]):
    with tab:
      # Gather all variations for this color specifically
      color_variations = []
      for op_name, variations in OPENING_DATABASE[color_key].items():
        for var_name, moves in variations.items():
          color_variations.append({
              "title": f"{op_name} ({var_name})",
              "player_color": chess.WHITE if color_key == "White" else chess.BLACK,
              "moves": moves,
          })

      if st.button(f"🔀 Shuffle All {color_key} Drills", key=f"shuffle_{color_key}"):
        shuffled_color = color_variations.copy()
        random.shuffle(shuffled_color)
        start_drill_session(shuffled_color)
        st.rerun()

      st.markdown("### Openings")
      for op_name, variations in OPENING_DATABASE[color_key].items():
        with st.expander(f"📁 {op_name}", expanded=True):
          # Shuffle option specifically for this opening family
          op_vars = [{
              "title": f"{op_name} ({v_name})",
              "player_color": chess.WHITE if color_key == "White" else chess.BLACK,
              "moves": v_moves,
          } for v_name, v_moves in variations.items()]

          if st.button(f"🔀 Shuffle {op_name} Variations", key=f"shuffle_{color_key}_{op_name}"):
            shuffled_op = op_vars.copy()
            random.shuffle(shuffled_op)
            start_drill_session(shuffled_op)
            st.rerun()

          st.markdown("---")
          for var_name, moves in variations.items():
            btn_label = f"▶️ {var_name}"
            if st.button(btn_label, key=f"btn_{color_key}_{op_name}_{var_name}", use_container_width=True):
              single_drill = [{
                  "title": f"{color_key} - {op_name}: {var_name}",
                  "player_color": chess.WHITE if color_key == "White" else chess.BLACK,
                  "moves": moves,
              }]
              start_drill_session(single_drill)
              st.rerun()

# ==========================================
# VIEW 2: THE DRILLING / GAME SCREEN
# ==========================================
else:
  current_drill = st.session_state.current_drills[st.session_state.drill_idx]

  # Top Bar: Back to Menu & Progress Counter
  col_back, col_prog = st.columns([1, 2])
  with col_back:
    if st.button("← Menu", use_container_width=True):
      st.session_state.app_mode = "menu"
      st.rerun()
  with col_prog:
    st.write(
        f"**Drill {st.session_state.drill_idx + 1} of {len(st.session_state.current_drills)}**"
    )

  st.subheader(current_drill["title"])
  color_label = (
      "White" if current_drill["player_color"] == chess.WHITE else "Black"
  )
  st.caption(f"Playing as **{color_label}**")
  st.info(st.session_state.feedback)

  # Render Chessboard
  ranks = (
      range(7, -1, -1)
      if current_drill["player_color"] == chess.WHITE
      else range(8)
  )
  files = (
      range(8)
      if current_drill["player_color"] == chess.WHITE
      else range(7, -1, -1)
  )

  square_images = []
  square_indices = []

  for r in ranks:
    for f in files:
      sq = chess.square(f, r)
      square_indices.append(sq)

      piece = st.session_state.board.piece_at(sq)
      is_light = (r + f) % 2 != 0
      bg_color = "#f0d9b5" if is_light else "#b58863"
      if st.session_state.selected_sq == sq:
        bg_color = "#cdd26a"

      piece_svg = ""
      if piece:
        raw_piece = chess.svg.piece(piece)
        inner = raw_piece.split(">", 1)[1].rsplit("</svg>", 1)[0]
        piece_svg = f'<g transform="scale(1.1)">{inner}</g>'

      sq_svg = (
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">'
          f'<rect width="50" height="50" fill="{bg_color}"/>{piece_svg}</svg>'
      )
      b64 = base64.b64encode(sq_svg.encode("utf-8")).decode("utf-8")
      square_images.append(f"data:image/svg+xml;base64,{b64}")

  clicked_idx = clickable_images(
      square_images,
      titles=[chess.square_name(sq) for sq in square_indices],
      div_style={
          "display": "grid",
          "grid-template-columns": "repeat(8, 1fr)",
          "max-width": "400px",
          "margin": "auto",
          "gap": "0px",
          "border": "2px solid #333",
      },
      img_style={"width": "100%", "display": "block", "cursor": "pointer"},
      key=f"drill_{st.session_state.drill_idx}_{st.session_state.move_idx}_{st.session_state.selected_sq}",
  )

  # Move handling logic
  if clicked_idx > -1:
    tapped_sq = square_indices[clicked_idx]

    if st.session_state.selected_sq is None:
      piece = st.session_state.board.piece_at(tapped_sq)
      if piece and piece.color == current_drill["player_color"]:
        st.session_state.selected_sq = tapped_sq
        st.rerun()
    else:
      if tapped_sq == st.session_state.selected_sq:
        st.session_state.selected_sq = None
        st.rerun()

      move_uci = (
          chess.square_name(st.session_state.selected_sq)
          + chess.square_name(tapped_sq)
      )
      st.session_state.selected_sq = None

      if st.session_state.move_idx < len(current_drill["moves"]):
        expected_uci = current_drill["moves"][st.session_state.move_idx]

        if move_uci == expected_uci:
          st.session_state.board.push(chess.Move.from_uci(move_uci))
          st.session_state.move_idx += 1

          # Play opponent response automatically if available
          while st.session_state.move_idx < len(current_drill["moves"]):
            if st.session_state.board.turn != current_drill["player_color"]:
              opp_move = current_drill["moves"][st.session_state.move_idx]
              st.session_state.board.push(chess.Move.from_uci(opp_move))
              st.session_state.move_idx += 1
            else:
              break

          if st.session_state.move_idx >= len(current_drill["moves"]):
            st.session_state.feedback = "🎉 Line complete! Great job."
          else:
            st.session_state.feedback = "Correct! Keep going..."
        else:
          st.session_state.feedback = f"Incorrect ({move_uci}). Try again!"
      st.rerun()

  # In-drill Navigation Footer
  col_reset, col_next = st.columns(2)
  with col_reset:
    if st.button("🔄 Reset Board", use_container_width=True):
      load_current_drill()
      st.rerun()

  with col_next:
    if st.session_state.drill_idx < len(st.session_state.current_drills) - 1:
      if st.button("Next Drill →", use_container_width=True):
        st.session_state.drill_idx += 1
        load_current_drill()
        st.rerun()
    else:
      if st.button("🏁 Finish Session", use_container_width=True):
        st.session_state.app_mode = "menu"
        st.rerun()
