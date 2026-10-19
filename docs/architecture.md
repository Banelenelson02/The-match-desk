# Architecture

Current: browser -> local HTTP API -> isolated Session -> exact event reducer -> metric cards.

Planned: synthetic stream -> statistics/tools -> Analyst -> Story Editor -> Evidence Reviewer -> deterministic final checks -> timed overlays and recap.

The agents are not implemented in this starter. Keep exact arithmetic in code. Review final rendered text, not only the upstream analyst draft. Corrections must invalidate dependent claims; never silently reuse an old review after a data revision.

Azure target: Foundry for model access and one Container App for the web application. Verify account access, current SDK contracts, model availability and costs before implementation. No paid services are provisioned here.
