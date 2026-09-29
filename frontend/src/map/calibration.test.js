import { test } from 'node:test'
import assert from 'node:assert/strict'
import { calibrate, legacyPoints, project, unproject, cornerKeys } from './calibration.js'
const base = { topLeft: unproject({ x: 1000, y: 2000 }), topRight: unproject({ x: 1200, y: 2000 }), bottomLeft: unproject({ x: 1000, y: 1900 }) }
const near = (actual, expected, tolerance = 1e-5) => assert.ok(Math.abs(actual-expected) < tolerance, `${actual} != ${expected}`)
const check = (actual, expected) => { for (const key of cornerKeys) { near(project(actual[key]).x, project(expected[key]).x); near(project(actual[key]).y, project(expected[key]).y) } }
test('zero points retain the initial placement', () => check(calibrate([], base).corners, base))
test('one arbitrary image point translates without changing scale', () => {
  const p = { x: 0.5, y: 0.5, ...unproject({x: 2100, y: 2950}) }
  const result = calibrate([p], base)
  near(project(result.corners.topLeft).x, 2000); near(project(result.corners.topLeft).y, 3000)
  near(project(result.corners.topRight).x - project(result.corners.topLeft).x, 200)
  check(calibrate([p], result.corners).corners, result.corners)
})
test('two points rotate and uniformly scale the initial placement', () => {
  const points = [{x:0,y:0,...unproject({x:3000,y:4000})}, {x:1,y:0,...unproject({x:3000,y:4400})}]
  const result = calibrate(points, base)
  near(project(result.corners.bottomLeft).x, 3200); near(project(result.corners.bottomLeft).y, 4000)
  check(calibrate(points, result.corners).corners, result.corners)
})
const affine = (x,y) => ({x: 10000+300*x+50*y, y:20000+30*x-150*y})
const point = (x,y) => ({x,y,...unproject(affine(x,y))})
test('three interior points recover all corners of an affine transform', () => {
  const result=calibrate([point(.1,.1),point(.8,.2),point(.3,.9)], base)
  near(project(result.corners.topLeft).x,10000); near(project(result.corners.bottomLeft).y,19850)
  result.residuals.forEach(r=>near(r,0))
})
test('all additional points influence least squares and expose residuals', () => {
  const points=[point(0,0),point(1,0),point(0,1),point(1,1),point(.5,.5)]
  const exact=calibrate(points,base)
  points[4]={x:.5,y:.5,...unproject({x:affine(.5,.5).x+10,y:affine(.5,.5).y})}
  const adjusted=calibrate(points,base)
  near(project(adjusted.corners.topLeft).x-project(exact.corners.topLeft).x,2)
  assert.ok(adjusted.residuals.every(r=>r>1))
})
test('legacy corners retain their alignment',()=>check(calibrate(legacyPoints(base),base).corners,base))
test('incomplete, coincident and collinear point sets are rejected',()=>{
  assert.throws(()=>calibrate([{x:null,y:0,lat:0,lng:0}],base))
  assert.throws(()=>calibrate([point(0,0),point(0,0)],base))
  assert.throws(()=>calibrate([point(0,0),point(.5,.5),point(1,1)],base))
  assert.throws(()=>calibrate([{...point(0,0),x:2}],base))
})
