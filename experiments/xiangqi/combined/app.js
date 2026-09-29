import { createInitialBoard, getLegalMoves, applyMove, getGameStatus } from './engine.js';

const names = {
  red: { rook: '车', horse: '马', elephant: '相', advisor: '仕', general: '帅', cannon: '炮', soldier: '兵' },
  black: { rook: '车', horse: '马', elephant: '象', advisor: '士', general: '将', cannon: '炮', soldier: '卒' }
};
const sideName = side => side === 'red' ? '红方' : '黑方';
const coordinate = p => `${String.fromCharCode(65 + p.x)}${p.y + 1}`;
const same = (a, b) => a && b && a.x === b.x && a.y === b.y;
const $ = id => document.getElementById(id);
let board = createInitialBoard(), turn = 'red', selected = null, legal = [], flipped = false;
let history = [], focus = { x: 0, y: 9 }, status = getGameStatus(board, turn);
const squares = new Map();

function drawLines() {
  const lines = [];
  for (let y = 0; y < 10; y++) lines.push(`<path d="M50 ${50 + y * 100}H850"/>`);
  for (let x = 0; x < 9; x++) {
    const px = 50 + x * 100;
    lines.push(`<path d="M${px} 50V450M${px} 550V950"/>`);
  }
  lines.push('<path d="M50 450V550M850 450V550M350 50L550 250M550 50L350 250M350 750L550 950M550 750L350 950"/>');
  lines.push('<text x="215" y="515">楚河</text><text x="615" y="515">汉界</text>');
  $('board-lines').innerHTML = lines.join('');
}

function announce(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}

function statusMessage() {
  if (status.over) return `本局结束：${sideName(status.winner)}获胜（${status.reason}）。可悔棋或重新开始。`;
  if (status.inCheck) return `${sideName(turn)}被将军，请选择合法着应将。`;
  return `${sideName(turn)}行棋，请选择己方棋子。`;
}

function render(message = statusMessage(), error = false) {
  const activeSquare = document.activeElement?.classList.contains('square') ? document.activeElement : null;
  status = getGameStatus(board, turn);
  const last = history.at(-1);
  const positions = [];
  for (let row = 0; row < 10; row++) for (let col = 0; col < 9; col++) positions.push({ x: flipped ? 8 - col : col, y: flipped ? 9 - row : row });
  for (const p of positions) {
    const key = `${p.x},${p.y}`;
    let button = squares.get(key);
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.dataset.x = p.x;
      button.dataset.y = p.y;
      button.addEventListener('click', () => activate(p));
      button.addEventListener('focus', () => { focus = p; updateTabStops(); });
      button.addEventListener('keydown', event => navigate(event, p));
      squares.set(key, button);
    }
    const piece = board[p.y][p.x], isLegal = legal.some(to => same(to, p)), isSelected = same(selected, p);
    button.className = ['square', piece ? 'occupied' : '', isLegal ? 'legal' : '', isSelected ? 'selected' : '', same(last?.from, p) || same(last?.to, p) ? 'last' : '', piece?.type === 'general' && piece.side === turn && status.inCheck ? 'checked' : ''].filter(Boolean).join(' ');
    button.innerHTML = piece ? `<span class="piece ${piece.side}" aria-hidden="true">${names[piece.side][piece.type]}</span>` : '';
    button.setAttribute('aria-label', `${coordinate(p)}，${piece ? sideName(piece.side) + names[piece.side][piece.type] : '空位'}${isSelected ? '，已选中' : ''}${isLegal ? (piece ? '，可以吃子' : '，可落子') : ''}`);
    button.setAttribute('aria-pressed', String(Boolean(isSelected)));
    button.setAttribute('aria-disabled', String(status.over));
    $('board').append(button);
  }
  updateTabStops();
  activeSquare?.focus({ preventScroll: true });
  $('turn-text').textContent = status.over ? `${sideName(status.winner)}获胜` : `${sideName(turn)}${history.length ? '行棋' : '先行'}${status.inCheck ? ' · 将军' : ''}`;
  document.querySelector('.turn-mark').className = `turn-mark ${status.over ? status.winner : turn}`;
  $('ply-count').textContent = status.over ? '本局结束' : `第 ${Math.floor(history.length / 2) + 1} 回合`;
  $('move-count').textContent = `${history.length} 手`;
  $('undo').disabled = !history.length;
  $('top-side').textContent = flipped ? '红方' : '黑方';
  $('bottom-side').textContent = flipped ? '黑方' : '红方';
  $('orientation').textContent = flipped ? '黑方在下' : '红方在下';
  $('empty-history').hidden = history.length > 0;
  $('history').replaceChildren(...history.map((move, index) => {
    const li = document.createElement('li');
    const counter = document.createElement('span'); counter.className = 'move-index'; counter.textContent = `${index + 1}.`;
    const text = document.createElement('span'); text.className = move.side; text.textContent = move.text;
    li.append(counter, text); return li;
  }));
  $('history').scrollTop = $('history').scrollHeight;
  announce(message, error);
}

function updateTabStops() {
  for (const button of squares.values()) button.tabIndex = Number(button.dataset.x) === focus.x && Number(button.dataset.y) === focus.y ? 0 : -1;
}

function navigate(event, p) {
  if (event.key === 'Escape') { selected = null; legal = []; render('已取消选择。' + statusMessage()); return; }
  const vectors = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  const vector = vectors[event.key];
  if (!vector) return;
  event.preventDefault();
  const direction = flipped ? -1 : 1;
  const next = { x: p.x + vector[0] * direction, y: p.y + vector[1] * direction };
  squares.get(`${next.x},${next.y}`)?.focus();
}

function activate(p) {
  if (status.over) { announce(statusMessage()); return; }
  const piece = board[p.y][p.x];
  if (same(selected, p)) { selected = null; legal = []; render('已取消选择。' + statusMessage()); return; }
  if (piece?.side === turn) {
    selected = p; legal = getLegalMoves(board, p, turn);
    render(`已选${sideName(turn)}${names[turn][piece.type]}（${coordinate(p)}），${legal.length ? `有 ${legal.length} 个合法落点。` : '暂无合法落点，请选择其他棋子。'}`);
    return;
  }
  if (!selected) { announce(`请先选择${sideName(turn)}棋子。`, true); return; }
  const result = applyMove(board, selected, p, turn);
  if (!result.ok) { announce(result.reason, true); return; }
  const moving = board[selected.y][selected.x];
  const text = `${sideName(turn)}${names[turn][moving.type]} ${coordinate(selected)} → ${coordinate(p)}${piece ? `，吃${names[piece.side][piece.type]}` : ''}`;
  history.push({ board, side: turn, from: { ...selected }, to: { ...p }, text });
  board = result.board; turn = turn === 'red' ? 'black' : 'red'; selected = null; legal = [];
  status = getGameStatus(board, turn);
  render(`${text}。${statusMessage()}`);
}

$('undo').addEventListener('click', () => {
  const previous = history.pop();
  if (!previous) return;
  board = previous.board; turn = previous.side; selected = null; legal = [];
  status = getGameStatus(board, turn);
  render(`已悔棋一步。${statusMessage()}`);
});
$('flip').addEventListener('click', () => { flipped = !flipped; render(`棋盘已翻转，${flipped ? '黑方' : '红方'}在下。${statusMessage()}`); });
$('restart').addEventListener('click', () => {
  board = createInitialBoard(); turn = 'red'; history = []; selected = null; legal = [];
  status = getGameStatus(board, turn);
  render('新的一局，红方先行。');
});
drawLines();
render('红方先行，请选择一枚红方棋子。');
