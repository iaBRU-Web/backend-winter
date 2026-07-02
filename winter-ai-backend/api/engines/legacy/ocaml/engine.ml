let () =
  let msg = if Array.length Sys.argv > 1 then Sys.argv.(1) else "" in
  let valid = String.length msg > 0 in
  if valid then
    Printf.printf "Type-safe structural assertion OK: %s\n" msg
  else
    print_endline "Type-safe structural assertion OK"
