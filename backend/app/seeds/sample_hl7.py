"""Seeded HL7v2 ADT^A01 message — the demo source for the ``hl7v2`` connector.

Synthetic patient only. Segments are CR-terminated per the HL7v2 spec (what
``hl7apy`` expects). This is the file-based stand-in for a real ADT feed: in a
deployment the hl7v2 connector would be pointed at the hospital's message stream;
here it defaults to this seed so the project works standalone.
"""

SAMPLE_ADT_A01 = (
    "MSH|^~\\&|HOSP|FAC|RECV|RECV|20260530120000||ADT^A01|MSG001|P|2.5\r"
    "EVN|A01|20260530120000\r"
    "PID|1||PAT001^^^FAC^MR||Romaguera^Kent^^^^^L||19400109|M\r"
    "PV1|1|I|WARD3B\r"
)
