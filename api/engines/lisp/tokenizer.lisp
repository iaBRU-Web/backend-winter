;;;; Winter AI - LISP symbolic tokenizer
;;;; Real Common Lisp code executed by SBCL (not simulated).
;;;; Usage: sbcl --script tokenizer.lisp "<prompt text>"
;;;; Prints a genuine S-expression built from the input, e.g.:
;;;;   (QUERY |what| |is| |photosynthesis|)

(defun clean-word (w)
  (string-trim '(#\, #\. #\! #\? #\; #\: #\" #\') w))

(defun tokenize (text)
  (let ((words '())
        (current (make-string-output-stream)))
    (loop for ch across text
          do (if (member ch '(#\Space #\Tab #\Newline))
                 (let ((w (get-output-stream-string current)))
                   (when (> (length w) 0) (push w words)))
                 (write-char ch current)))
    (let ((last (get-output-stream-string current)))
      (when (> (length last) 0) (push last words)))
    (nreverse words)))

(defun build-sexpr (tokens)
  (format nil "(QUERY~{ |~A|~})"
          (mapcar (lambda (w) (string-downcase (clean-word w)))
                   (remove-if (lambda (w) (= 0 (length (clean-word w)))) tokens))))

(let* ((args sb-ext:*posix-argv*)
       (text (if (>= (length args) 2) (second args) "")))
  (let* ((tokens (tokenize text))
         (sexpr (build-sexpr tokens)))
    (format t "~A~%" sexpr)))
