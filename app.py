import csv
import io
import json
import random
import chess
import chess.pgn
import streamlit as st
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(page_title="Chess Opening Trainer", layout="centered")

# Compact mobile padding so the board fits comfortably without scrolling
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# 2. Load & Parse Opening Database from openings.csv
@st.cache_data
def load_openings_from_csv(filepath="openings.csv"):
  database = {"White": {}, "Black": {}}
  seen_counts = {}

  try:
    with open(filepath, mode="r", encoding="utf-8-sig") as f:
      reader = csv.DictReader(f)
      for row in reader:
        color = row.get("Color", "").strip().capitalize()
        opening = row.get("Opening", "").strip()
        variation = row.get("Variation", "").strip()
        moves_str = row.get("Moves", "").strip()

        if color not in database or not opening or not variation or not moves_str:
          continue

        # Auto-number duplicate variation titles so none get overwritten
        key = (color, opening, variation)
        seen_counts[key] = seen_counts.get(key, 0) + 1
        display_variation = (
            variation
            if seen_counts[key] == 1
            else f"{variation} #{seen_counts[key]}"
        )

        pgn_io = io.StringIO(moves_str)
        game = chess.pgn.read_game(pgn_io)
        if game:
          uci_moves = [move.uci() for move in game.mainline_moves()]
          if uci_moves:
            database[color].setdefault(opening, {})[display_variation] = uci_moves
  except FileNotFoundError:
    st.error("Could not find `openings.csv` in your repository.")

  return database


OPENING_DATABASE = load_openings_from_csv()

# 3. Initialize Session State
if "app_mode" not in st.session_state:
  st.session_state.app_mode = "menu"
if "current_drills" not in st.session_state:
  st.session_state.current_drills = []
if "drill_idx" not in st.session_state:
  st.session_state.drill_idx = 0
if "board_reset_counter" not in st.session_state:
  st.session_state.board_reset_counter = 0


def start_drill_session(drills_list):
  st.session_state.current_drills = drills_list
  st.session_state.drill_idx = 0
  st.session_state.board_reset_counter += 1
  st.session_state.app_mode = "drilling"


def render_animated_chessboard(drill, session_nonce):
  """Renders an interactive chessboard.js widget with animations, highlights, and legal move dots."""
  orientation = "white" if drill["player_color"] == chess.WHITE else "black"
  moves_json = json.dumps(drill["moves"])

  html_code = f"""
  <!DOCTYPE html>
  <html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link rel="stylesheet" href="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.css">
    <style>
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
      body {{
        margin: 0;
        padding: 4px 0 8px 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        display: flex;
        flex-direction: column;
        align-items: center;
        background: transparent;
      }}
      #status-banner {{
        width: 100%;
        max-width: 400px;
        padding: 10px 14px;
        margin-bottom: 10px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
        background-color: #e8f1fb;
        color: #0c3b6e;
        transition: background-color 0.2s ease, color 0.2s ease;
      }}
      #status-banner.error {{
        background-color: #fde8e8;
        color: #9b1c1c;
      }}
      #status-banner.success {{
        background-color: #def7ec;
        color: #03543f;
      }}
      #board {{
        width: 100%;
        max-width: 400px;
        touch-action: none;
      }}
      /* Last-move & tap selection highlights */
      .highlight-last {{
        box-shadow: inset 0 0 3px 3px rgba(246, 246, 105, 0.85);
        background-color: rgba(246, 246, 105, 0.45) !important;
      }}
      .highlight-selected {{
        box-shadow: inset 0 0 3px 3px rgba(105, 190, 246, 0.9);
        background-color: rgba(105, 190, 246, 0.45) !important;
      }}
      /* Legal move dot for empty destination squares */
      .square-55d63 {{
        position: relative;
      }}
      .legal-move-dot::after {{
        content: "";
        position: absolute;
        width: 30%;
        height: 30%;
        top: 35%;
        left: 35%;
        border-radius: 50%;
        background-color: rgba(20, 85, 30, 0.42);
        pointer-events: none;
        z-index: 10;
      }}
      /* Legal capture ring for squares containing an opponent piece */
      .legal-capture-ring::after {{
        content: "";
        position: absolute;
        width: 82%;
        height: 82%;
        top: 9%;
        left: 9%;
        border-radius: 50%;
        border: 4px solid rgba(20, 85, 30, 0.48);
        background-color: transparent;
        pointer-events: none;
        z-index: 10;
      }}
    </style>
  </head>
  <body>
    <div id="status-banner">Make your move...</div>
    <div id="board"></div>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
    <script src="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.js"></script>

    <script>
      // Nonce ensures Streamlit reloads cleanly on Reset / Next Drill: {session_nonce}
      const expectedMoves = {moves_json};
      const playerOrientation = "{orientation}";
      const playerTurnCode = playerOrientation === "white" ? "w" : "b";

      const game = new Chess();
      let moveIdx = 0;
      let selectedSquare = null;
      let legalTargets = [];
      let lastMove = null;
      let isAnimating = false;

      const statusEl = document.getElementById("status-banner");

      function setStatus(text, type = "info") {{
        statusEl.textContent = text;
        statusEl.className = type === "info" ? "" : type;
      }}

      function computeLegalTargets(square) {{
        if (!square) return [];
        const moves = game.moves({{ square: square, verbose: true }});
        return moves.map(m => m.to);
      }}

      function clearLegalMarkers() {{
        $("#board .square-55d63").removeClass("legal-move-dot legal-capture-ring");
      }}

      function showLegalMarkers(square) {{
        clearLegalMarkers();
        legalTargets = computeLegalTargets(square);
        legalTargets.forEach(targetSq => {{
          const occupant = game.get(targetSq);
          const $sqEl = $("#board .square-" + targetSq);
          if (occupant) {{
            $sqEl.addClass("legal-capture-ring");
          }} else {{
            $sqEl.addClass("legal-move-dot");
          }}
        }});
      }}

      function updateHighlights() {{
        $("#board .square-55d63").removeClass("highlight-last highlight-selected");
        clearLegalMarkers();

        if (lastMove) {{
          $("#board .square-" + lastMove.from).addClass("highlight-last");
          $("#board .square-" + lastMove.to).addClass("highlight-last");
        }}
        if (selectedSquare) {{
          $("#board .square-" + selectedSquare).addClass("highlight-selected");
          showLegalMarkers(selectedSquare);
        }} else {{
          legalTargets = [];
        }}
      }}

      function parseUci(uci) {{
        return {{
          from: uci.slice(0, 2),
          to: uci.slice(2, 4),
          promotion: uci.length > 4 ? uci[4] : "q"
        }};
      }}

      function playOpponentMoveIfNeeded() {{
        if (moveIdx >= expectedMoves.length) {{
          setStatus("🎉 Line complete! Great job.", "success");
          return;
        }}
        if (game.turn() !== playerTurnCode) {{
          isAnimating = true;
          setTimeout(() => {{
            const oppMoveObj = parseUci(expectedMoves[moveIdx]);
            const executed = game.move(oppMoveObj);
            if (executed) {{
              lastMove = {{ from: executed.from, to: executed.to }};
              moveIdx++;
              board.position(game.fen(), true); // true = smooth slide animation
              updateHighlights();
            }}
            isAnimating = false;
            if (moveIdx >= expectedMoves.length) {{
              setStatus("🎉 Line complete! Great job.", "success");
            }} else {{
              setStatus("Your turn...");
            }}
          }}, 280);
        }}
      }}

      function attemptPlayerMove(source, target) {{
        if (isAnimating || moveIdx >= expectedMoves.length) return false;
        if (game.turn() !== playerTurnCode) return false;

        // Check if move is even legal in chess
        const testGame = new Chess(game.fen());
        const legalCheck = testGame.move({{ from: source, to: target, promotion: "q" }});
        if (!legalCheck) return false;

        const attemptedUci = source + target + (legalCheck.promotion ? legalCheck.promotion : "");
        const targetUci = expectedMoves[moveIdx];

        if (attemptedUci === targetUci || (source + target) === targetUci.slice(0, 4)) {{
          const executed = game.move(parseUci(targetUci));
          lastMove = {{ from: executed.from, to: executed.to }};
          moveIdx++;
          selectedSquare = null;
          board.position(game.fen(), true);
          updateHighlights();

          if (moveIdx >= expectedMoves.length) {{
            setStatus("🎉 Line complete! Great job.", "success");
          }} else {{
            setStatus("Correct! Keep going...");
            playOpponentMoveIfNeeded();
          }}
          return true;
        }} else {{
          setStatus(`Incorrect (${{legalCheck.san}}). Try again!`, "error");
          return false;
        }}
      }}

      // Drag-and-drop handlers
      function onDragStart(source, piece) {{
        if (isAnimating || moveIdx >= expectedMoves.length) return false;
        if (game.turn() !== playerTurnCode) return false;
        if ((playerTurnCode === "w" && piece.search(/^b/) !== -1) ||
            (playerTurnCode === "b" && piece.search(/^w/) !== -1)) {{
          return false;
        }}
        selectedSquare = source;
        updateHighlights();
        return true;
      }}

      function onDrop(source, target) {{
        if (source === target) return; // Allow tap handler to manage selection
        const valid = attemptPlayerMove(source, target);
        selectedSquare = null;
        updateHighlights();
        if (!valid) {{
          return "snapback";
        }}
      }}

      function onSnapEnd() {{
        board.position(game.fen(), false);
        updateHighlights();
      }}

      const board = Chessboard("board", {{
        draggable: true,
        position: "start",
        orientation: playerOrientation,
        moveSpeed: 200,
        snapbackSpeed: 180,
        snapSpeed: 80,
        pieceTheme: "https://chessboardjs.com/img/chesspieces/wikipedia/{{piece}}.png",
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
      }});

      // Tap-to-move support (ideal for mobile touchscreens)
      $("#board").on("click", ".square-55d63", function() {{
        if (isAnimating || moveIdx >= expectedMoves.length) return;
        const clickedSq = $(this).attr("data-square");
        const pieceOnSq = game.get(clickedSq);

        if (!selectedSquare) {{
          if (pieceOnSq && pieceOnSq.color === playerTurnCode) {{
            selectedSquare = clickedSq;
            updateHighlights();
          }}
        }} else {{
          if (clickedSq === selectedSquare) {{
            selectedSquare = null;
            updateHighlights();
            return;
          }}
          // If tapping another friendly piece, switch selection and refresh legal dots
          if (pieceOnSq && pieceOnSq.color === playerTurnCode) {{
            selectedSquare = clickedSq;
            updateHighlights();
            return;
          }}
          const success = attemptPlayerMove(selectedSquare, clickedSq);
          if (!success) {{
            selectedSquare = null;
            updateHighlights();
          }}
        }}
      }});

      $(window).resize(() => board.resize());

      // Auto-play White's opening move if user is drilling Black
      playOpponentMoveIfNeeded();
    </script>
  </body>
  </html>
  """

  components.html(html_code, height=470)


# ==========================================
# VIEW 1: THE MENU SCREEN
# ==========================================
if st.session_state.app_mode == "menu":
  st.title("Cigarette-Chess: Openings")
  st.write("Time to get good")

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

  if all_variations:
    if st.button("🔀 Shuffle All Drills", use_container_width=True):
      shuffled = all_variations.copy()
      random.shuffle(shuffled)
      start_drill_session(shuffled)
      st.rerun()

  st.divider()

  tab_white, tab_black = st.tabs(["White Repertoire", "Black Repertoire"])

  for tab, color_key in zip([tab_white, tab_black], ["White", "Black"]):
    with tab:
      if not OPENING_DATABASE[color_key]:
        st.info(f"No {color_key} openings found in openings.csv yet.")
        continue

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
        with st.expander(f"📁 {op_name}", expanded=False):
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

  # Render the smooth animated board
  render_animated_chessboard(
      current_drill,
      session_nonce=f"{st.session_state.drill_idx}_{st.session_state.board_reset_counter}",
  )

  col_reset, col_next = st.columns(2)
  with col_reset:
    if st.button("🔄 Reset Board", use_container_width=True):
      st.session_state.board_reset_counter += 1
      st.rerun()

  with col_next:
    if st.session_state.drill_idx < len(st.session_state.current_drills) - 1:
      if st.button("Next Drill →", use_container_width=True):
        st.session_state.drill_idx += 1
        st.session_state.board_reset_counter += 1
        st.rerun()
    else:
      if st.button("🏁 Finish Session", use_container_width=True):
        st.session_state.app_mode = "menu"
        st.rerun()
