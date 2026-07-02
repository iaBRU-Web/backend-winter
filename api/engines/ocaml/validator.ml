(* Winter AI - OCaml type/encoding validation engine
   Real OCaml, compiled ahead-of-time to a native binary in the Docker
   build stage (ocamlfind ocamlopt), not simulated.
   Usage: ./validator "<text>"
   Prints JSON: {"valid": true/false, "byte_len": N, "char_len": N, "engine": "ocaml"} *)

let utf8_char_len text =
  (* Count Unicode codepoints in a UTF-8 encoded string by counting
     bytes that are NOT UTF-8 continuation bytes (10xxxxxx). *)
  let count = ref 0 in
  String.iter
    (fun c ->
      let b = Char.code c in
      if b land 0xC0 <> 0x80 then incr count)
    text;
  !count

let is_valid_utf8 text =
  try
    let len = String.length text in
    let i = ref 0 in
    let ok = ref true in
    while !ok && !i < len do
      let b0 = Char.code text.[!i] in
      let extra =
        if b0 land 0x80 = 0x00 then 0
        else if b0 land 0xE0 = 0xC0 then 1
        else if b0 land 0xF0 = 0xE0 then 2
        else if b0 land 0xF8 = 0xF0 then 3
        else -1
      in
      if extra < 0 || !i + extra >= len then ok := false
      else begin
        for k = 1 to extra do
          let bk = Char.code text.[!i + k] in
          if bk land 0xC0 <> 0x80 then ok := false
        done;
        i := !i + extra + 1
      end
    done;
    !ok
  with _ -> false

let json_escape s =
  let buf = Buffer.create (String.length s) in
  String.iter
    (fun c ->
      match c with
      | '"' -> Buffer.add_string buf "\\\""
      | '\\' -> Buffer.add_string buf "\\\\"
      | c -> Buffer.add_char buf c)
    s;
  Buffer.contents buf

let () =
  let text = if Array.length Sys.argv > 1 then Sys.argv.(1) else "" in
  let valid = is_valid_utf8 text in
  let byte_len = String.length text in
  let char_len = if valid then utf8_char_len text else -1 in
  Printf.printf
    "{\"valid\": %s, \"byte_len\": %d, \"char_len\": %d, \"engine\": \"ocaml\", \"input\": \"%s\"}\n"
    (if valid then "true" else "false")
    byte_len char_len (json_escape text)
