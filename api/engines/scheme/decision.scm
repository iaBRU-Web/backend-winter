#!/usr/bin/env guile
!#
;; ============================================================================
;; Winter AI -- Scheme Decision Engine (GNU Guile)
;; Real forward-chaining `cond` dispatch over tokenised user input.
;; Invoked as:  guile decision.scm "<lang>" "<token1,token2,...>"
;; Emits a small line-based protocol on stdout: KEY: value
;; ============================================================================

(use-modules (ice-9 rdelim)
             (ice-9 regex)
             (srfi srfi-1))

;; ---- Rule tables (real S-expression data, not string hacks) --------------
(define greeting-words
  '((en . (hello hi hey greetings))
    (fr . (bonjour salut bonsoir))
    (rw . (muraho bite))))

(define thanks-words
  '((en . (thanks thank))
    (fr . (merci))
    (rw . (murakoze))))

(define wellbeing-words
  '((en . (how are you doing fine))
    (fr . (comment allez ca va))
    (rw . (amakuru bite))))

(define identity-words
  '((en . (who are you name yourself))
    (fr . (qui es appelles))
    (rw . (witwa uri))))

(define farewell-words
  '((en . (bye goodbye later))
    (fr . (au revoir salut))
    (rw . (murabeho))))

(define positive-words '(good great love happy excellent nice awesome bien content))
(define negative-words '(bad hate sad angry terrible awful mauvais triste))

;; ---- Helpers ---------------------------------------------------------------
(define (str->symlist s)
  (map string->symbol
       (filter (lambda (x) (> (string-length x) 0))
                (string-split s #\,))))

(define (intersect? tokens words)
  (not (null? (lset-intersection eq? tokens words))))

(define (words-for table lang)
  (let ((entry (assq (string->symbol lang) table)))
    (if entry (cdr entry) '())))

;; ---- The actual decision cond (this IS the reasoning engine) --------------
(define (classify-intent tokens lang)
  (cond
    ((intersect? tokens (words-for greeting-words lang))  'greeting)
    ((intersect? tokens (words-for thanks-words lang))    'thanks)
    ((intersect? tokens (words-for wellbeing-words lang)) 'wellbeing)
    ((intersect? tokens (words-for identity-words lang))  'identity)
    ((intersect? tokens (words-for farewell-words lang))  'farewell)
    (else 'lookup)))

(define (sentiment-score tokens)
  (let ((pos (length (lset-intersection eq? tokens positive-words)))
        (neg (length (lset-intersection eq? tokens negative-words))))
    (cond ((> pos neg) 'positive)
          ((> neg pos) 'negative)
          (else 'neutral))))

(define (confidence tokens lang intent)
  (if (eq? intent 'lookup)
      0.35
      (/ (exact->inexact (length (lset-intersection eq? tokens (words-for
                            (case intent
                              ((greeting) greeting-words)
                              ((thanks) thanks-words)
                              ((wellbeing) wellbeing-words)
                              ((identity) identity-words)
                              ((farewell) farewell-words)
                              (else greeting-words))
                            lang))))
         (max 1 (length tokens)))))

;; ---- Entry point ------------------------------------------------------------
(define (main args)
  (let* ((lang   (if (> (length args) 1) (list-ref args 1) "en"))
         (raw    (if (> (length args) 2) (list-ref args 2) ""))
         (tokens (str->symlist raw))
         (intent (classify-intent tokens lang))
         (sent   (sentiment-score tokens))
         (conf   (confidence tokens lang intent)))
    (display "ENGINE: Scheme (GNU Guile)") (newline)
    (display (string-append "INTENT: " (symbol->string intent))) (newline)
    (display (string-append "SENTIMENT: " (symbol->string sent))) (newline)
    (display (string-append "CONFIDENCE: " (number->string (exact->inexact conf)))) (newline)
    (display (string-append
      "TRACE: (cond ((intersect? tokens '"
      (with-output-to-string (lambda () (write (words-for greeting-words lang))))
      ") 'greeting) ... (else 'lookup)) => '" (symbol->string intent)))
    (newline)))

(main (command-line))
