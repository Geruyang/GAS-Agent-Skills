// Coordinates are always black-at-top, independent of the view orientation.
const inside = p => p && Number.isInteger(p.x) && Number.isInteger(p.y) && p.x >= 0 && p.x < 9 && p.y >= 0 && p.y < 10;
const opposite = side => side === 'red' ? 'black' : 'red';
const label = side => side === 'red' ? '红方' : '黑方';
const copy = board => board.map(row => row.map(piece => piece ? {...piece} : null));
const palace = (x,y,side) => x >= 3 && x <= 5 && (side === 'red' ? y >= 7 && y <= 9 : y >= 0 && y <= 2);

export function createInitialBoard() {
  const board = Array.from({length:10}, () => Array(9).fill(null));
  const rank = ['rook','horse','elephant','advisor','general','advisor','elephant','horse','rook'];
  for (const side of ['black','red']) {
    const back = side === 'black' ? 0 : 9;
    rank.forEach((type,x) => { board[back][x] = {side,type}; });
    for (const x of [1,7]) board[side === 'black' ? 2 : 7][x] = {side,type:'cannon'};
    for (const x of [0,2,4,6,8]) board[side === 'black' ? 3 : 6][x] = {side,type:'soldier'};
  }
  return board;
}

function findGeneral(board,side) {
  for (let y=0;y<10;y++) for (let x=0;x<9;x++)
    if (board[y][x]?.side === side && board[y][x].type === 'general') return {x,y};
  return null;
}

function between(board,from,to) {
  const dx=Math.sign(to.x-from.x), dy=Math.sign(to.y-from.y);
  let count=0;
  for(let x=from.x+dx,y=from.y+dy;x!==to.x||y!==to.y;x+=dx,y+=dy) if(board[y][x]) count++;
  return count;
}

// Attack geometry is independent of enemy legal-move filtering, avoiding recursion
// and correctly treating defended squares even when the defender is pinned.
function attacks(board,from,to) {
  const piece=board[from.y][from.x];
  const dx=to.x-from.x,dy=to.y-from.y, ax=Math.abs(dx),ay=Math.abs(dy);
  if(!piece || (!ax&&!ay)) return false;
  switch(piece.type) {
    case 'rook': return (dx===0||dy===0) && between(board,from,to)===0;
    case 'cannon': return (dx===0||dy===0) && between(board,from,to)===(board[to.y][to.x]?1:0);
    case 'horse': return ax===2&&ay===1 ? !board[from.y][from.x+Math.sign(dx)] : ax===1&&ay===2 && !board[from.y+Math.sign(dy)][from.x];
    case 'elephant': return ax===2&&ay===2 && (piece.side==='red'?to.y>=5:to.y<=4) && !board[from.y+dy/2][from.x+dx/2];
    case 'advisor': return ax===1&&ay===1&&palace(to.x,to.y,piece.side);
    case 'general':
      if(dx===0 && board[to.y][to.x]?.type==='general' && board[to.y][to.x].side!==piece.side) return between(board,from,to)===0;
      return ax+ay===1&&palace(to.x,to.y,piece.side);
    case 'soldier': return (dx===0&&dy===(piece.side==='red'?-1:1)) || (dy===0&&ax===1&&(piece.side==='red'?from.y<=4:from.y>=5));
    default: return false;
  }
}

export function isInCheck(board,side) {
  const general=findGeneral(board,side);
  if(!general) return true;
  for(let y=0;y<10;y++) for(let x=0;x<9;x++)
    if(board[y][x]?.side===opposite(side) && attacks(board,{x,y},general)) return true;
  return false;
}

function moved(board,from,to) {
  const result=copy(board);
  result[to.y][to.x]=result[from.y][from.x];
  result[from.y][from.x]=null;
  return result;
}

export function getLegalMoves(board,from,side) {
  if(!inside(from)||board[from.y][from.x]?.side!==side||!findGeneral(board,side)) return [];
  const moves=[];
  for(let y=0;y<10;y++) for(let x=0;x<9;x++) {
    const to={x,y};
    if(board[y][x]?.side!==side && attacks(board,from,to) && !isInCheck(moved(board,from,to),side)) moves.push(to);
  }
  return moves;
}

export function applyMove(board,from,to,side) {
  if(!inside(from)||!inside(to)) return {ok:false,board,reason:'落点超出棋盘范围'};
  if(board[from.y][from.x]?.side!==side) return {ok:false,board,reason:`请先选择${label(side)}棋子`};
  if(!getLegalMoves(board,from,side).some(p=>p.x===to.x&&p.y===to.y))
    return {ok:false,board,reason:'此步不合法：请按棋子走法落子，且不能使己方被将军'};
  return {ok:true,board:moved(board,from,to)};
}

export function getGameStatus(board,sideToMove) {
  const enemy=opposite(sideToMove), inCheck=isInCheck(board,sideToMove);
  if(!findGeneral(board,sideToMove)) return {over:true,winner:enemy,reason:`${label(sideToMove)}将已被吃，${label(enemy)}获胜`,inCheck};
  if(!findGeneral(board,enemy)) return {over:true,winner:sideToMove,reason:`${label(enemy)}将已被吃，${label(sideToMove)}获胜`,inCheck};
  for(let y=0;y<10;y++) for(let x=0;x<9;x++)
    if(board[y][x]?.side===sideToMove && getLegalMoves(board,{x,y},sideToMove).length)
      return {over:false,winner:null,reason:inCheck?'将军，请应将':'对局进行中',inCheck};
  return {over:true,winner:enemy,reason:`${inCheck?'将死':'困毙'}，${label(enemy)}获胜`,inCheck};
}
