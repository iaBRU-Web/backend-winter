#!/usr/bin/env sbcl --script
(let ((arg (if (> (length sb-ext:*posix-argv*) 1)
               (nth 1 sb-ext:*posix-argv*)
               "")))
  (format t "(eval '~A)~%" arg))
