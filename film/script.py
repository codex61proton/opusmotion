"""Narration + caption markup. Each segment is one TTS take; each string in `cards` is one caption card.
Markup: `/` line break, `!` punch line, `^w^` red accent, `~w~` redaction reveal, `%w%` huge, `#w#` mono,
`[shown=spoken]` pronunciation override, `_` joins words in one token. Sources: docs/sources.md."""

SEGMENTS = [
    # ---- cold open
    ("open", 0.0, [
        "In [January_1964,=January nineteen sixty-four,] / !the U.S. Navy ^intercepted^",
        "a secret Soviet radar— / !by listening to ~the_Moon.~",
    ]),
    # ---- FILE 01: MOON BOUNCE  (Eliot, Studies in Intelligence 11:2, 1967)
    ("u2", 0.55, [
        "A [U-2=U two] had spotted / !its giant antenna",
        "at #[Sary_Shagan,=Sari Shagan,]# / the Soviet missile test range.",
    ]),
    ("horizon", 0.35, [
        "But radar waves / !travel in ^straight^ lines.",
        "From deep inside the [USSR,=U.S.S.R.,] / !they skim past the horizon",
        "and / !vanish into space.",
    ]),
    ("nuke", 0.35, [
        "In [1962,=nineteen sixty-two,] it was heard briefly— / !bounced off the ionized cloud",
        "of a / !^Soviet_nuclear_test.^",
        "They needed / !a steadier mirror.",
    ]),
    ("moon", 0.25, [
        "%The_Moon.%",
    ]),
    ("geometry", 0.45, [
        "When it sat low / !on the radar's horizon",
        "and was also up / !over America,",
        "a sliver of each pulse / !bounced back down.",
    ]),
    ("faint", 0.3, [
        "That echo was more than / !a ^million_billion^",
        "times weaker than the signal / !ten miles from the radar.",
        "Only / ![150-foot=hundred-and-fifty-foot] dishes / could hear it.",
    ]),
    ("sites", 0.3, [
        "The Navy's dish on / !Chesapeake Bay got it first.",
        "The CIA's, at Stanford, / !joined in [1965.=nineteen sixty-five.]",
        "Geometry allowed / !about [^18_hours^=eighteen hours] a month.",
    ]),
    ("found", 0.3, [
        "It was enough to find / !computer-controlled scanning,",
        "a / !spread-spectrum mode,",
        "about / ![25_megawatts=twenty-five megawatts] of peak power.",
        "Verdict: / !a new ^anti-missile^ radar.",
    ]),
    ("practice", 0.3, [
        "Soviet operators even / !locked it onto the Moon—",
        "!for practice.",
    ]),
    # ---- FILE 02: THE LUNIK  (Finer, Studies in Intelligence; Wheelon & Graybeal, Studies 5:4)
    ("bridge", 0.9, [
        "The CIA got even closer / !to Soviet Moon hardware.",
    ]),
    ("exhibit", 0.3, [
        "A touring Soviet exhibition / !showed off a ^Lunik^:",
        "the final stage / !of a Moon rocket.",
        "Surely, / !a ~mock-up.~",
    ]),
    ("real", 0.35, [
        "!It wasn't.",
        "U.S. intelligence officers / !spent a day with it:",
        "a real production vehicle, / !engine removed.",
    ]),
    ("icbm", 0.3, [
        "That data helped the CIA / !measure the Soviet [ICBM:=I.C.B.M.:]",
        "![18,000_pounds=eighteen thousand pounds] / thrown *[3,800_miles=thirty-eight hundred miles]*.",
    ]),
    ("borrow", 0.4, [
        "Later, to copy its / !factory markings,",
        "the CIA / !^borrowed^ it. / Overnight.",
    ]),
    ("truck", 0.35, [
        "It left as / !the day's last truck.",
        "At the final turnoff, / !canvas went over the crate",
        "and a new driver / !took the wheel.",
        "The real one spent the night / !in a hotel.",
    ]),
    ("yard", 0.3, [
        "In a rented salvage yard, / !four specialists opened the roof,",
        "unbolted the base, / !and slipped inside—",
        "!shoes off.",
    ]),
    ("dawn", 0.35, [
        "By [7_a.m.,=seven A.M.,] / !the truck was at the rail yard.",
        "The Soviet checker / !showed ~no_surprise.~",
    ]),
    ("results", 0.3, [
        "The markings pointed to / !the probable manufacturer,",
        "and showed it was / !the ^fifth^ one built.",
    ]),
    ("nosign", 0.3, [
        "The CIA saw no sign / !the Soviets ever knew.",
    ]),
    ("end", 0.5, [
        "Both files stayed classified / !until the [1990s.=nineteen-nineties.]",
    ]),
]
