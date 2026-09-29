import test from 'node:test';
import assert from 'node:assert/strict';
import { createInitialBoard, getLegalMoves, applyMove, getGameStatus, isInCheck } from './engine.js';

const empty = () => Array.from({ length: 10 }, () => Array(9).fill(null));
const p = (side, type) => ({ side, type });
const at = (x, y) => ({ x, y });
const has = (board, from, to, side) => getLegalMoves(board, from, side).some(m => m.x === to.x && m.y === to.y);
function fixture() {
  const b = empty(); b[0][3] = p('black', 'general'); b[9][4] = p('red', 'general'); return b;
}
const opposite = side => side === 'red' ? 'black' : 'red';
function mirror(board) {
  return board.toReversed().map(row => row.toReversed().map(piece => piece ? { side: opposite(piece.side), type: piece.type } : null));
}
const mirrorPoint = point => at(8 - point.x, 9 - point.y);
const sorted = moves => moves.map(m => `${m.x},${m.y}`).sort();

test('opening has 44 legal moves per side and color inversion preserves every legal destination', () => {
  const board = createInitialBoard(); const reversed = mirror(board); let total = 0;
  for (let y = 0; y < 10; y++) for (let x = 0; x < 9; x++) {
    if (board[y][x]?.side !== 'red') continue;
    const legal = getLegalMoves(board, at(x, y), 'red'); total += legal.length;
    assert.deepEqual(sorted(legal.map(mirrorPoint)), sorted(getLegalMoves(reversed, mirrorPoint(at(x, y)), 'black')));
  }
  assert.equal(total, 44);
});

test('all eight horse jumps use the correct orthogonal leg', () => {
  const b = fixture(); b[5][4] = p('red', 'horse');
  for (const [dx, dy, lx, ly] of [[2,1,1,0],[2,-1,1,0],[-2,1,-1,0],[-2,-1,-1,0],[1,2,0,1],[-1,2,0,1],[1,-2,0,-1],[-1,-2,0,-1]]) {
    assert.ok(has(b, at(4,5), at(4+dx,5+dy), 'red'));
    b[5+ly][4+lx] = p('black','soldier');
    assert.equal(has(b,at(4,5),at(4+dx,5+dy),'red'),false);
    b[5+ly][4+lx] = null;
  }
});

test('moving a cannon screen away may answer check; adding a second screen also answers check', () => {
  const b = fixture(); b[1][4] = p('black','cannon'); b[5][4] = p('red','rook');
  assert.equal(isInCheck(b,'red'),true);
  assert.ok(has(b,at(4,5),at(5,5),'red'));
  b[7][0] = p('red','rook');
  assert.ok(has(b,at(0,7),at(4,7),'red'));
});

test('a general cannot capture a piece defended by a rook', () => {
  const b = fixture(); b[8][4] = p('black','soldier'); b[8][0] = p('black','rook');
  assert.equal(has(b,at(4,9),at(4,8),'red'),false);
});

test('flying general capture is legal on an unobstructed file and ends the game', () => {
  const b = empty(); b[0][4] = p('black','general'); b[9][4] = p('red','general');
  const result = applyMove(b,at(4,9),at(4,0),'red');
  assert.ok(result.ok); assert.deepEqual(getGameStatus(result.board,'black'),{over:true,winner:'red',reason:'缺将判负',inCheck:true});
  assert.deepEqual(getLegalMoves(result.board,at(4,0),'red'),[]);
});

test('black stalemate and checkmate are losses with identical mirrored outcomes', () => {
  const b=fixture(); b[8][3]=p('black','rook'); b[8][5]=p('black','rook');
  const stalemate=getGameStatus(mirror(b),'black');
  assert.equal(stalemate.over,true); assert.equal(stalemate.winner,'red'); assert.equal(stalemate.inCheck,false);
  b[1][4]=p('black','rook');
  const mate=getGameStatus(mirror(b),'black');
  assert.equal(mate.over,true); assert.equal(mate.winner,'red'); assert.equal(mate.inCheck,true);
});

test('invalid coordinates, invalid side and same-square moves are rejected without mutation', () => {
  const b=createInitialBoard(), before=structuredClone(b);
  for(const from of [null,at(0.5,6),at(NaN,6),at(0,Infinity)]) assert.deepEqual(getLegalMoves(b,from,'red'),[]);
  assert.deepEqual(getLegalMoves(b,at(0,6),'green'),[]);
  for(const to of [null,at(0.1,5),at(0,6),at(9,5)]) assert.equal(applyMove(b,at(0,6),to,'red').ok,false);
  assert.deepEqual(b,before);
});

test('immutable source boards can be queried and moved', () => {
  const b=createInitialBoard();
  b.forEach(row => {row.forEach(piece => {if(piece) Object.freeze(piece);}); Object.freeze(row);}); Object.freeze(b);
  assert.equal(applyMove(b,at(0,6),at(0,5),'red').ok,true);
  assert.equal(getGameStatus(b,'red').over,false);
});

test('deterministic 100-ply legal playout preserves kings, turn legality, source values and piece count', () => {
  let b=createInitialBoard(), side='red', seed=93021, played=0;
  for(let ply=0;ply<100;ply++) {
    const state=getGameStatus(b,side); if(state.over) break;
    const options=[];
    for(let y=0;y<10;y++) for(let x=0;x<9;x++) for(const to of getLegalMoves(b,at(x,y),side)) options.push({from:at(x,y),to});
    assert.ok(options.length);
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const move=options[seed%options.length], before=structuredClone(b), count=b.flat().filter(Boolean).length;
    const captured=Boolean(b[move.to.y][move.to.x]);
    const next=applyMove(b,move.from,move.to,side);
    assert.ok(next.ok); assert.deepEqual(b,before); assert.equal(isInCheck(next.board,side),false);
    assert.equal(next.board.flat().filter(Boolean).length,count-Number(captured));
    assert.equal(next.board.flat().filter(piece=>piece?.type==='general').length,2);
    b=next.board; side=opposite(side); played++;
  }
  assert.ok(played>=30,`Only ${played} plies played`);
});
