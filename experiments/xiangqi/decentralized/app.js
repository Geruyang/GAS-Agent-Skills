import {createInitialBoard,getLegalMoves,applyMove,getGameStatus} from './engine.js';

const $ = id => document.getElementById(id);
const names = {
  red:{rook:'车',horse:'马',elephant:'相',advisor:'仕',general:'帅',cannon:'炮',soldier:'兵'},
  black:{rook:'车',horse:'马',elephant:'象',advisor:'士',general:'将',cannon:'炮',soldier:'卒'}
};
const sideName = side => side==='red' ? '红方' : '黑方';
let board=createInitialBoard(), side='red', selected=null, flipped=false;
let history=[], records=[], lastMove=null;
let status=getGameStatus(board,side);
const same=(a,b)=>a && b && a.x===b.x && a.y===b.y;

function announce(message, error=false) {
  $('status').textContent=message;
  $('status').classList.toggle('error',error);
}

function boardArt() {
  const lines=[];
  for(let y=50;y<=950;y+=100) lines.push(`<path d="M50 ${y}H850"/>`);
  for(let x=50;x<=850;x+=100) lines.push(`<path d="M${x} 50V450 M${x} 550V950"/>`);
  lines.push('<path d="M50 450V550 M850 450V550 M350 50L550 250 M550 50L350 250 M350 750L550 950 M550 750L350 950"/>');
  return `<svg viewBox="0 0 900 1000" aria-hidden="true"><g fill="none" stroke="#8d7350" stroke-width="2">${lines.join('')}</g><g fill="#84653f" font-family="KaiTi,STKaiti,serif" font-size="36" text-anchor="middle"><text x="250" y="514">楚 河</text><text x="650" y="514">汉 界</text></g></svg>`;
}

function renderBoard(focusPoint=null) {
  const legal=selected ? getLegalMoves(board,selected,side) : [];
  $('board').innerHTML=boardArt();
  for(let row=0;row<10;row++) for(let col=0;col<9;col++) {
    const x=flipped ? 8-col : col, y=flipped ? 9-row : row;
    const point={x,y}, piece=board[y][x];
    const canMove=legal.some(p=>same(p,point));
    const cell=document.createElement('button');
    cell.type='button';
    cell.className=`cell ${piece ? `occupied ${piece.side}` : ''}${same(selected,point)?' selected':''}${canMove?' legal':''}${same(lastMove?.from,point)||same(lastMove?.to,point)?' last':''}`;
    cell.style.left=`${(col+.5)/9*100}%`;
    cell.style.top=`${(row+.5)/10*100}%`;
    cell.dataset.x=x; cell.dataset.y=y;
    const identity=piece ? `${sideName(piece.side)}${names[piece.side][piece.type]}` : '空位';
    cell.setAttribute('aria-label',`${identity}，第${x+1}列第${y+1}行${canMove?'，可落子':''}`);
    cell.setAttribute('aria-pressed',String(!!same(selected,point)));
    if(piece) {const disc=document.createElement('span');disc.className='piece';disc.textContent=names[piece.side][piece.type];cell.append(disc);}
    cell.addEventListener('click',()=>choose(point));
    cell.addEventListener('keydown',event=>{
      const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
      if(!delta)return;
      event.preventDefault();
      const nx=col+delta[0],ny=row+delta[1];
      if(nx<0||nx>8||ny<0||ny>9)return;
      focusCell({x:flipped?8-nx:nx,y:flipped?9-ny:ny});
    });
    $('board').append(cell);
  }
  if(focusPoint) focusCell(focusPoint);
}

function focusCell(point) {
  $('board').querySelector(`[data-x="${point.x}"][data-y="${point.y}"]`)?.focus({preventScroll:true});
}

function renderInfo() {
  $('turn').textContent=status.over ? `${sideName(status.winner)}胜 · ${status.reason}` : `${sideName(side)}行棋${status.inCheck?' · 将军':''}`;
  $('turn').className=`turn ${status.over ? status.winner : side}`;
  $('move-count').textContent=`第 ${Math.floor(records.length/2)+1} 回合`;
  $('piece-count').textContent=`棋盘 ${board.flat().filter(Boolean).length} 子`;
  $('record-count').textContent=`${records.length} 步`;
  $('undo').disabled=history.length===0;
  $('top-player').textContent=flipped?'红方':'黑方';
  $('bottom-player').textContent=flipped?'黑方':'红方';
  $('orientation').textContent=flipped?'黑方在下':'红方在下';
  $('flip').setAttribute('aria-pressed',String(flipped));
  $('empty-record').hidden=records.length>0;
  $('records').replaceChildren(...records.map((record,index)=>{
    const li=document.createElement('li'),number=document.createElement('span'),text=document.createElement('span');
    number.className='step';number.textContent=String(index+1).padStart(2,'0');
    text.className=`record-${record.side}`;text.textContent=record.text;
    li.append(number,text);return li;
  }));
  $('records').scrollTop=$('records').scrollHeight;
}

function turnMessage() {
  return status.over ? `${sideName(status.winner)}获胜，原因：${status.reason}。可悔棋继续或重新开始。`
    : status.inCheck ? `${sideName(side)}被将军，请先解除将军。` : `轮到${sideName(side)}，请选择棋子。`;
}

function choose(point) {
  if(status.over) {announce(turnMessage());return;}
  const piece=board[point.y][point.x];
  if(piece?.side===side) {
    selected=same(selected,point)?null:point;
    renderBoard(point);
    announce(selected ? `已选${sideName(side)}${names[side][piece.type]}。${getLegalMoves(board,point,side).length?'请选择标记的落点。':'此棋暂无合法落点，请选择其他棋子。'}` : turnMessage());
    return;
  }
  if(!selected) {announce(`请先选择${sideName(side)}棋子。`,true);return;}
  const result=applyMove(board,selected,point,side);
  if(!result.ok) {announce(result.reason,true);return;}
  const moving=board[selected.y][selected.x],capture=board[point.y][point.x];
  history.push({board,side,lastMove});
  records.push({side,text:`${sideName(side)}${names[side][moving.type]} ${selected.x+1},${selected.y+1} → ${point.x+1},${point.y+1}${capture?` · 吃${names[capture.side][capture.type]}`:''}`});
  lastMove={from:selected,to:point};board=result.board;selected=null;
  side=side==='red'?'black':'red';status=getGameStatus(board,side);
  renderBoard(point);renderInfo();announce(turnMessage());
}

$('undo').addEventListener('click',()=>{
  if(!history.length)return;
  const previous=history.pop();
  board=previous.board;side=previous.side;lastMove=previous.lastMove;selected=null;records.pop();
  status=getGameStatus(board,side);renderBoard();renderInfo();announce(`已悔棋。${turnMessage()}`);
});
$('flip').addEventListener('click',()=>{
  flipped=!flipped;renderBoard();renderInfo();announce(`棋盘已翻转，${flipped?'黑方':'红方'}在下。${turnMessage()}`);
});
$('restart').addEventListener('click',()=>{
  board=createInitialBoard();side='red';selected=null;history=[];records=[];lastMove=null;
  status=getGameStatus(board,side);renderBoard();renderInfo();announce('新局已开始，红方先行。');
});
renderBoard();renderInfo();
