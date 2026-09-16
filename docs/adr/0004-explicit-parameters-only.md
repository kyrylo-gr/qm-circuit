# Show a parameter only when the code sets it, detected by protobuf field presence

A box shows `amp`, `duration`, `chirp`, `truncate`, `condition` or `target` only when the protobuf has that optional field set (`HasField`), which happens only when the user passed it. The diagram reflects the decisions written in the code, and config values stay hidden: offline there is no config to read them from (ADR-0001), and showing them would bury the choices the physicist made. `* amp(1.0)` written in code counts as explicit and is shown, even though it changes nothing.
