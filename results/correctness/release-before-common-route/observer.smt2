(declare-const x Int) (declare-const y Int) (declare-const b Bool)
(assert (and (or (= x 10) (= x 0) (> y -99999999999999999999999))
 (= (+ x y) (+ y x)) (= (ite b (- x) (* x 2)) (ite b (- x) (* x 2)))
 (= (not b) (= x y))))