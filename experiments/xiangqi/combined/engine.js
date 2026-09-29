// Pure Xiangqi rules. Coordinates always refer to black at the top, red below.
const SIDES = ['red', 'black'];
const other = side => side === 'red' ? 'black' : 'red';
const inside = p => p && Number.isInteger(p.x) && Number.isInteger(p.y) && p.x >= 0 && p.x < 9 && p.y >= 0 && p.y < 10;
const clone = board => board.map(row => row.map(p => p ? { ...p } : null));
const palace = (p, side) => p.x >= 3 && p.x <= 5 && (side === 'red' ? p.y >= 7 && p.y <= 9 : p.y >= 0 && p.y <= 2);
const generalAt = (board, side) => {
  for (let y = 0; y < 10; y++) for (let x = 0; x < 9; x++) {
    if (board[y][x]?.side === side && board[y][x].type === 'general') return { x, y };
  }
  return null;
};

export function createInitialBoard() {
  const board = Array.from({ length: 10 }, () => Array(9).fill(null));
  const back = ['rook', 'horse', 'elephant', 'advisor', 'general', 'advisor', 'elephant', 'horse', 'rook'];
  for (const side of SIDES) {
    const y = side === 'red' ? 9 : 0;
    back.forEach((type, x) => { board[y][x] = { side, type }; });
    for (const x of [1, 7]) board[side === 'red' ? 7 : 2][x] = { side, type: 'cannon' };
    for (const x of [0, 2, 4, 6, 8]) board[side === 'red' ? 6 : 3][x] = { side, type: 'soldier' };
  }
  return board;
}

function between(board, from, to) {
  const dx = Math.sign(to.x - from.x), dy = Math.sign(to.y - from.y);
  let count = 0;
  for (let x = from.x + dx, y = from.y + dy; x !== to.x || y !== to.y; x += dx, y += dy) {
    if (board[y][x]) count++;
  }
  return count;
}

// Attack geometry is deliberately separate from legal moves: pinned enemy pieces
// still attack geometrically, and check detection never recursively calls itself.
function reaches(board, from, to) {
  if (!inside(from) || !inside(to) || (from.x === to.x && from.y === to.y)) return false;
  const p = board[from.y][from.x], target = board[to.y][to.x];
  if (!p || target?.side === p.side) return false;
  const dx = to.x - from.x, dy = to.y - from.y, ax = Math.abs(dx), ay = Math.abs(dy);
  switch (p.type) {
    case 'rook': return (dx === 0 || dy === 0) && between(board, from, to) === 0;
    case 'cannon': return (dx === 0 || dy === 0) && between(board, from, to) === (target ? 1 : 0);
    case 'horse':
      if (ax === 2 && ay === 1) return !board[from.y][from.x + Math.sign(dx)];
      if (ax === 1 && ay === 2) return !board[from.y + Math.sign(dy)][from.x];
      return false;
    case 'elephant': return ax === 2 && ay === 2 && (p.side === 'red' ? to.y >= 5 : to.y <= 4) && !board[from.y + dy / 2][from.x + dx / 2];
    case 'advisor': return ax === 1 && ay === 1 && palace(to, p.side);
    case 'general':
      if (target?.type === 'general' && dx === 0 && between(board, from, to) === 0) return true;
      return ax + ay === 1 && palace(to, p.side);
    case 'soldier':
      if (dx === 0 && dy === (p.side === 'red' ? -1 : 1)) return true;
      return dy === 0 && ax === 1 && (p.side === 'red' ? from.y <= 4 : from.y >= 5);
    default: return false;
  }
}

export function isInCheck(board, side) {
  const king = generalAt(board, side);
  if (!king) return true;
  for (let y = 0; y < 10; y++) for (let x = 0; x < 9; x++) {
    if (board[y][x]?.side === other(side) && reaches(board, { x, y }, king)) return true;
  }
  return false;
}

function moved(board, from, to) {
  const result = clone(board);
  result[to.y][to.x] = result[from.y][from.x];
  result[from.y][from.x] = null;
  return result;
}

export function getLegalMoves(board, from, side) {
  if (!SIDES.includes(side) || !inside(from) || board[from.y][from.x]?.side !== side || !generalAt(board, side) || !generalAt(board, other(side))) return [];
  const moves = [];
  for (let y = 0; y < 10; y++) for (let x = 0; x < 9; x++) {
    const to = { x, y };
    if (reaches(board, from, to) && !isInCheck(moved(board, from, to), side)) moves.push(to);
  }
  return moves;
}

export function applyMove(board, from, to, side) {
  if (!inside(to) || !getLegalMoves(board, from, side).some(p => p.x === to.x && p.y === to.y)) {
    return { ok: false, board, reason: '此着不合法：请遵守棋子走法，并确保己方将帅安全。' };
  }
  return { ok: true, board: moved(board, from, to) };
}

export function getGameStatus(board, sideToMove) {
  const opponent = other(sideToMove);
  if (!generalAt(board, sideToMove)) return { over: true, winner: opponent, reason: '缺将判负', inCheck: true };
  if (!generalAt(board, opponent)) return { over: true, winner: sideToMove, reason: '对方缺将', inCheck: false };
  const inCheck = isInCheck(board, sideToMove);
  for (let y = 0; y < 10; y++) for (let x = 0; x < 9; x++) {
    if (board[y][x]?.side === sideToMove && getLegalMoves(board, { x, y }, sideToMove).length) {
      return { over: false, winner: null, reason: inCheck ? '将军' : '对弈中', inCheck };
    }
  }
  return { over: true, winner: opponent, reason: inCheck ? '将死' : '困毙', inCheck };
}
