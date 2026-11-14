import base64
import chess
import chess.svg
import streamlit as st
from streamlit_clickable_images import clickable_images

# 1. Page Configuration (Mobile-friendly centered layout)
st.set_page_config(page_title="Opening Trainer", layout="centered")

# 2. Flashcard Database (Add your own opening lines here!)
# Moves are in UCI format (e.g., "d2d4" = pawn from d2 to d4)
OPENINGS = [
    {
        "title": "London System: Main Line Setup",
        "player_color": chess.WHITE,
        "moves": ["d2d4", "d7d5", "c1f4", "g8f6", "e2e3", "e7e6", "g1f3"],
    },
    {
        "title": "French Defense: Advance Variation",
        "player_color": chess.BLACK,
        "moves": ["e2e4", "e7e6", "d2d4", "d7d5", "e4e5", "c7c5", "c2c3"],
    },
]

# 3. Initialize App Memory (Session State)
if "card_idx" not in st.session_state:
  st.session_state.card_idx = 0
  st.session_state.move_idx = 0
  st.session_state.board = chess.Board()
  st.session_state.selected_sq = None
  st.session_state.feedback = "Tap a piece to make your move."

current_card = OPENINGS[st.session_state.card_idx]


# Helper to auto-play opponent moves when it's not the user's turn
def play_opponent_moves():
  while st.session_state.move_idx < len(current_card["moves"]):
    if st.session_state.board.turn != current_card["player_color"]:
      opp_move_uci = current_card["moves"][st.session_state.move_idx]
      st.session_state.board.push(chess.Move.from_uci(opp_move_uci))
      st.session_state.move_idx += 1
    else:
      break


# Trigger opponent's first move immediately if the user is playing Black
play_opponent_moves()

# 4. Header & Flashcard Prompt UI
st.subheader(f"Card {st.session_state.card_idx + 1}: {current_card['title']}")
color_label = (
    "White" if current_card["player_color"] == chess.WHITE else "Black"
)
st.caption(f"You are playing as **{color_label}**")
st.info(st.session_state.feedback)

# 5. Render the 8x8 Board as Clickable Squares
# Flip board orientation if playing as Black
ranks = (
    range(7, -1, -1)
    if current_card["player_color"] == chess.WHITE
    else range(8)
)
files = (
    range(8)
    if current_card["player_color"] == chess.WHITE
    else range(7, -1, -1)
)

square_images = []
square_indices = []

for r in ranks:
  for f in files:
    sq = chess.square(f, r)
    square_indices.append(sq)

    # Highlight the currently selected square in yellow
    fill = {sq: "#f6f669cc"} if st.session_state.selected_sq == sq else {}

    # Generate an individual square SVG using python-chess
    # Note: Using full board SVG slices or clean individual square SVGs
    piece = st.session_state.board.piece_at(sq)
    is_light = (r + f) % 2 != 0
    bg_color = "#f0d9b5" if is_light else "#b58863"
    if st.session_state.selected_sq == sq:
      bg_color = "#cdd26a"

    piece_svg = ""
    if piece:
      # Extract piece glyph from chess.svg
      raw_piece = chess.svg.piece(piece)
      # Strip outer <svg> wrapper to embed inside square
      inner = raw_piece.split(">", 1)[1].rsplit("</svg>", 1)[0]
      piece_svg = f'<g transform="scale(1.1)">{inner}</g>'

    sq_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">'
        f'<rect width="50" height="50" fill="{bg_color}"/>{piece_svg}</svg>'
    )
    b64 = base64.b64encode(sq_svg.encode("utf-8")).decode("utf-8")
    square_images.append(f"data:image/svg+xml;base64,{b64}")

# Display the 64 squares in an 8-column responsive grid
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
    key=f"board_{st.session_state.card_idx}_{st.session_state.move_idx}_{st.session_state.selected_sq}",
)

# 6. Handle Tap / Move Validation Logic
if clicked_idx > -1:
  tapped_sq = square_indices[clicked_idx]

  # Step A: Select a piece
  if st.session_state.selected_sq is None:
    piece = st.session_state.board.piece_at(tapped_sq)
    if piece and piece.color == current_card["player_color"]:
      st.session_state.selected_sq = tapped_sq
      st.rerun()

  # Step B: Attempt a move to the second tapped square
  else:
    if tapped_sq == st.session_state.selected_sq:
      st.session_state.selected_sq = None  # Deselect if tapped twice
      st.rerun()

    move_uci = (
        chess.square_name(st.session_state.selected_sq)
        + chess.square_name(tapped_sq)
    )
    st.session_state.selected_sq = None

    if st.session_state.move_idx < len(current_card["moves"]):
      expected_uci = current_card["moves"][st.session_state.move_idx]

      if move_uci == expected_uci:
        st.session_state.board.push(chess.Move.from_uci(move_uci))
        st.session_state.move_idx += 1
        play_opponent_moves()

        if st.session_state.move_idx >= len(current_card["moves"]):
          st.session_state.feedback = (
              "Line complete! Tap 'Next Card' to continue."
          )
        else:
          st.session_state.feedback = "Correct! Keep going..."
      else:
        st.session_state.feedback = (
            f"Incorrect ({move_uci}). Try again!"
        )
    st.rerun()

# 7. Navigation Controls
col1, col2 = st.columns(2)
with col1:
  if st.button("Reset Card", use_container_width=True):
    st.session_state.move_idx = 0
    st.session_state.board = chess.Board()
    st.session_state.selected_sq = None
    st.session_state.feedback = "Card reset. Try again!"
    st.rerun()

with col2:
  if st.button("Next Card", use_container_width=True):
    st.session_state.card_idx = (st.session_state.card_idx + 1) % len(OPENINGS)
    st.session_state.move_idx = 0
    st.session_state.board = chess.Board()
    st.session_state.selected_sq = None
    st.session_state.feedback = "Tap a piece to make your move."
    st.rerun()
