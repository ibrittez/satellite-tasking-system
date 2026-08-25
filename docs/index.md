# Documentation

The README states the design decisions in summary form. These documents carry the detail.

| document                                                             | scope                                                                 |
| -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [architecture.md](architecture.md)                                   | process topology, layering, the two ports, the resource invariant     |
| [ipc.md](ipc.md)                                                     | transport: channel types, addressing, message envelopes, termination  |
| [allocator.md](allocator.md)                                         | the allocation algorithm, stage by stage, with the diff of each stage |
| [allocator_load_spread_example.md](allocator_load_spread_example.md) | worked example of the reconstruction pass, iteration by iteration     |
| [web.md](web.md)                                                     | the HTTP mode: where the station runs, what it reuses, its limits     |

Suggested order: `architecture.md` for the shape of the system, `ipc.md` for how the
processes talk, `allocator.md` for the algorithm, `web.md` for the second front end.
