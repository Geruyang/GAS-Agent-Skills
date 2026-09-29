// Rules are independent of the interface. Coordinates always keep black at y=0.
const opposite = side => side === 'red' ? 'black' : 'red';
const validSide = side => side === 'red' || side === 'black';
const inside = pos => pos && Number.isInteger(pos.x) && Number.isInteger(pos.y)
  && pos.x >= 0 && pos.x < 9 && pos.y >= 0 && pos.y < 10;
const clone = board => board.map(row => row.map(piece => piece ? {...piece} : null));
const palace = (pos, side) => pos.x >= 3 && pos.x <= 5
  && (side === 'red' ? pos.y >= 7 && pos.y <= 9 : pos.y >= 0 && pos.y <= 2);

export function createInitialBoard() {
  const board = Array.from({length:10}, () => Array(9).fill(null));
  const back = ['rook','horse','elephant','advisor','general','advisor','elephant','horse','rook'];
  for (const side of ['black','red']) {
    const red = side === 'red';
    back.forEach((type,x) => board[red ? 9 : 0][x] = {side,type});
    for (const x of [1,7]) board[red ? 7 : 2][x] = {side,type:'cannon'};
    for (const x of [0,2,4,6,8]) board[red ? 6 : 3][x] = {side,type:'soldier'};
  }
  return board;
}

function generalPosition(board, side) {
  for (let y=0; y<10; y++) for (let x=0; x<9; x++) {
    if (board[y][x]?.side === side && board[y][x].type === 'general') return {x,y};
  }
  return null;
}

function intervening(board, from, to) {
  const sx = Math.sign(to.x-from.x), sy = Math.sign(to.y-from.y);
  let count = 0;
  for (let x=from.x+sx, y=from.y+sy; x!==to.x || y!==to.y; x+=sx,y+=sy) {
    if (board[y][x]) count++;
  }
  return count;
}

// Geometric attacks deliberately do not recurse into legal moves: a pinned
// enemy still controls squares under the specified attack-map contract.
function reaches(board, from, to) {
  const piece = board[from.y][from.x], target = board[to.y][to.x];
  if (!piece || target?.side === piece.side) return false;
  const dx=to.x-from.x, dy=to.y-from.y, ax=Math.abs(dx), ay=Math.abs(dy);
  if (ax+ay === 0) return false;
  switch (piece.type) {
    case 'rook':
      return (dx===0 || dy===0) && intervening(board,from,to)===0;
    case 'cannon':
      return (dx===0 || dy===0) && intervening(board,from,to)===(target ? 1 : 0);
    case 'horse':
      if (ax===2 && ay===1) return !board[from.y][from.x+Math.sign(dx)];
      if (ax===1 && ay===2) return !board[from.y+Math.sign(dy)][from.x];
      return false;
    case 'elephant':
      return ax===2 && ay===2 && (piece.side==='red' ? to.y>=5 : to.y<=4)
        && !board[from.y+dy/2][from.x+dx/2];
    case 'advisor':
      return ax===1 && ay===1 && palace(to,piece.side);
    case 'general':
      if (dx===0 && target?.type==='general') return intervening(board,from,to)===0;
      return ax+ay===1 && palace(to,piece.side);
    case 'soldier': {
      const forward = piece.side==='red' ? -1 : 1;
      const crossed = piece.side==='red' ? from.y<=4 : from.y>=5;
      return (dx===0 && dy===forward) || (crossed && ay===0 && ax===1);
    }
    default: return false;
  }
}

export function isInCheck(board, side) {
  const general = generalPosition(board,side);
  if (!general) return true;
  for (let y=0; y<10; y++) for (let x=0; x<9; x++) {
    if (board[y][x]?.side === opposite(side) && reaches(board,{x,y},general)) return true;
  }
  return false;
}

function moved(board, from, to) {
  const next = clone(board);
  next[to.y][to.x] = next[from.y][from.x];
  next[from.y][from.x] = null;
  return next;
}

export function getLegalMoves(board, from, side) {
  if (!validSide(side) || !inside(from) || board[from.y][from.x]?.side !== side) return [];
  const moves = [];
  for (let y=0; y<10; y++) for (let x=0; x<9; x++) {
    const to = {x,y};
    if (reaches(board,from,to) && !isInCheck(moved(board,from,to),side)) moves.push(to);
  }
  return moves;
}

export function applyMove(board, from, to, side) {
  if (!inside(to) || !getLegalMoves(board,from,side).some(p => p.x===to.x && p.y===to.y)) {
    return {ok:false, board, reason:'这步不合法：请按棋子走法落子，并确保己方将帅安全。'};
  }
  return {ok:true,board:moved(board,from,to)};
}

export function getGameStatus(board, sideToMove) {
  for (const side of [sideToMove,opposite(sideToMove)]) {
    if (!generalPosition(board,side)) return {over:true,winner:opposite(side),reason:side==='red'?'红方缺将':'黑方缺将',inCheck:!!generalPosition(board,sideToMove) && isInCheck(board,sideToMove)};
  }
  const inCheck = isInCheck(board,sideToMove);
  for (let y=0; y<10; y++) for (let x=0; x<9; x++) {
    if (board[y][x]?.side===sideToMove && getLegalMoves(board,{x,y},sideToMove).length) {
      return {over:false,winner:null,reason:inCheck?'将军':'对弈中',inCheck};
    }
  }
  return {over:true,winner:opposite(sideToMove),reason:inCheck?'将死':'困毙',inCheck};
}
