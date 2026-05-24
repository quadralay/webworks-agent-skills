# Variant: link reference definition

The link reference definition still does real work in this variant. In order
to keep the assembly stage deterministic, the definition is declared once in
the source document and continues to work unchanged when the file is later
assembled. Downstream consumers MUST resolve the reference at assembly time;
the definition itself remains in place exactly as authored.

If the assembler rewrites the definition, the resolved link target changes,
and the rendered output diverges from the source intent.
