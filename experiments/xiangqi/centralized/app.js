import {createInitialBoard,getLegalMoves,applyMove,getGameStatus} from './engine.js';

const $=id=>document.getElementById(id);
const names={red:{rook:'车',horse:'马',elephant:'相',advisor:'仕',general:'帅',cannon:'炮',soldier:'兵'},black:{rook:'车',horse:'马',elephant:'象',advisor:'士',general:'将',cannon:'炮',soldier:'卒'}};
const sideName=side=>side==='red'?'红方':'黑方';
const coord=p=>`${String.fromCharCode(65+p.x)}${p.y+1}`;
let board=createInitialBoard(),turn='red',selected=null,legal=[],history=[],flipped=false,lastMove=null;
let status=getGameStatus(board,turn);

function boardArt(){
  let lines='';
  for(let y=0;y<10;y++) lines+=`<path d="M50 ${50+100*y}H850"/>`;
  for(let x=0;x<9;x++) lines+=x===0||x===8?`<path d="M${50+100*x} 50V950"/>`:`<path d="M${50+100*x} 50V450M${50+100*x} 550V950"/>`;
  lines+='<path d="M350 50L550 250M550 50L350 250M350 750L550 950M550 750L350 950"/>';
  $('board-art').innerHTML=`<g stroke="#806b48" stroke-width="2" fill="none">${lines}</g><g fill="#806b48" font-family="KaiTi,STKaiti,serif" font-size="38" text-anchor="middle"><text x="250" y="512">楚 河</text><text x="650" y="512">汉 界</text></g>`;
}

function tell(message,error=false){$('feedback').textContent=message;$('feedback').classList.toggle('error',error);}
function clearSelection(){selected=null;legal=[];}

function render(){
  const active=document.activeElement?.dataset;
  const focusCoord=active?.x!==undefined?{x:Number(active.x),y:Number(active.y)}:null;
  status=getGameStatus(board,turn);
  $('turn').textContent=status.over?`${sideName(status.winner)}获胜`:`${sideName(turn)}行棋`;
  $('turn').classList.toggle('black-turn',(status.winner||turn)==='black');
  $('status').textContent=status.over?status.reason:status.inCheck?'将军！请移动将帅、吃掉攻击棋子或挡住攻击。':`${sideName(turn)}请选择棋子，按标记落子。`;
  $('move-count').textContent=`第 ${Math.floor(history.length/2)+1} 回合`;
  $('ply-count').textContent=`${history.length} 步`;
  $('undo').disabled=history.length===0;
  $('top-player').textContent=flipped?'红方':'黑方';
  $('bottom-player').textContent=flipped?'黑方':'红方';
  $('top-player').style.color=flipped?'var(--red)':'var(--ink)';
  $('bottom-player').style.color=flipped?'var(--ink)':'var(--red)';
  $('orientation').textContent=flipped?'黑方在下':'红方在下';
  $('board').setAttribute('aria-label',`棋盘，${flipped?'红方在上、黑方在下':'黑方在上、红方在下'}。按方向键移动焦点，回车选子或落子。`);
  const fragment=document.createDocumentFragment();
  for(let vy=0;vy<10;vy++)for(let vx=0;vx<9;vx++){
    const x=flipped?8-vx:vx,y=flipped?9-vy:vy,piece=board[y][x];
    const cell=document.createElement('button');
    cell.type='button';cell.className='square';cell.dataset.x=x;cell.dataset.y=y;
    const isSelected=selected?.x===x&&selected?.y===y;
    const isLegal=legal.some(p=>p.x===x&&p.y===y);
    cell.classList.toggle('selected',isSelected);cell.classList.toggle('legal',isLegal);
    cell.classList.toggle('last',Boolean(lastMove&&[lastMove.from,lastMove.to].some(p=>p.x===x&&p.y===y)));
    cell.classList.toggle('in-check',Boolean(piece?.type==='general'&&piece.side===turn&&status.inCheck));
    cell.setAttribute('aria-pressed',String(isSelected));
    cell.setAttribute('aria-label',`${piece?sideName(piece.side)+names[piece.side][piece.type]:'空位'} ${coord({x,y})}${isSelected?'，已选中':''}${isLegal?'，可落子':''}`);
    if(piece){const disk=document.createElement('span');disk.className=`piece ${piece.side}`;disk.textContent=names[piece.side][piece.type];cell.append(disk);}
    cell.addEventListener('click',()=>activate({x,y}));
    cell.addEventListener('keydown',event=>{
      if(event.key==='Escape'){clearSelection();tell('已取消选择。');render();return;}
      const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
      if(!delta)return;event.preventDefault();
      const nx=vx+delta[0],ny=vy+delta[1];
      if(nx>=0&&nx<9&&ny>=0&&ny<10)$('squares').children[ny*9+nx].focus();
    });
    fragment.append(cell);
  }
  $('squares').replaceChildren(fragment);
  if(focusCoord)$('squares').querySelector(`[data-x="${focusCoord.x}"][data-y="${focusCoord.y}"]`)?.focus({preventScroll:true});
  renderHistory();
}

function renderHistory(){
  const records=$('records');records.replaceChildren();
  if(!history.length){const empty=document.createElement('p');empty.className='empty-record';empty.textContent='棋局初开，静候第一步。';records.append(empty);return;}
  for(let i=0;i<history.length;i+=2){
    const row=document.createElement('div');row.className='record-row';
    [String(i/2+1),history[i].notation,history[i+1]?.notation||'—'].forEach((value,index)=>{const cell=document.createElement('span');cell.textContent=value;if(index===1)cell.className='red-record';row.append(cell);});
    records.append(row);
  }
  records.scrollTop=records.scrollHeight;
}

function activate(to){
  if(status.over){tell('对局已结束。可悔棋继续，或重新开始。',true);return;}
  const piece=board[to.y][to.x];
  if(piece?.side===turn){
    if(selected?.x===to.x&&selected?.y===to.y){clearSelection();tell('已取消选择。');}
    else{selected=to;legal=getLegalMoves(board,to,turn);tell(legal.length?`已选${sideName(turn)}${names[turn][piece.type]}，有 ${legal.length} 个合法落点。`:'此棋子暂时无合法落点，请选择其他棋子。');}
    render();return;
  }
  if(!selected){tell(`现在轮到${sideName(turn)}，请先选择己方棋子。`,true);return;}
  const result=applyMove(board,selected,to,turn);
  if(!result.ok){tell(result.reason,true);return;}
  const moving=board[selected.y][selected.x];
  const notation=`${names[turn][moving.type]} ${coord(selected)}${piece?'×':'→'}${coord(to)}`;
  history.push({board,turn,lastMove,notation});
  lastMove={from:{...selected},to:{...to}};board=result.board;turn=turn==='red'?'black':'red';clearSelection();
  render();tell(piece?`已吃${sideName(piece.side)}${names[piece.side][piece.type]}。`:'落子完成。');
}

$('undo').addEventListener('click',()=>{const previous=history.pop();if(!previous)return;({board,turn,lastMove}=previous);clearSelection();render();tell('已撤回一步，恢复行棋方。');});
$('restart').addEventListener('click',()=>{board=createInitialBoard();turn='red';history=[];lastMove=null;clearSelection();render();tell('新局已开始，红方先行。');});
$('flip').addEventListener('click',()=>{flipped=!flipped;render();tell(`棋盘已翻转，${flipped?'黑方':'红方'}在下。`);});
boardArt();render();
