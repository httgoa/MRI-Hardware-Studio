# Design Note (placeholder): Decoupling Strategies + Open-Source Library Survey

> Open-ended survey notes, not executable steps. Land into `recipes/decoupling/` once mature.

## To survey
- **Decoupling strategy spectrum**: geometric overlap, inductive/capacitive decoupling networks, preamplifier decoupling, resistive decoupling (receive), transformer decoupling. Their respective applicable frequency bands/array topologies/costs.
- **Combining with open-source libraries** (per the user's explicit request to "combine with open-source libraries"): survey open-source tools usable for decoupling-network synthesis/optimization (e.g. scikit-rf for S-parameter/network synthesis, pyMRI/related coil-design libraries). Evaluate how to interface with the CST MCP pipeline (CST produces S-parameters → an open-source library synthesizes the decoupling network → fed back into the schematic).
- **Criterion**: inter-channel isolation <−15dB (or per application); decoupling should not significantly degrade single-channel B₁⁺ efficiency.

## Interface with existing assets
- S-parameter extraction: `driving/mcp-tool-map.md` (`cst_export_touchstone_tool` / schematic S-parameters).
- Feeding synthesized networks back: schematic-topology experience from `recipes/build/smith-matching.md`, `pitfalls/schematic-cosim.md`.

(TODO: fill in specific library names, versions, integration-script sketch.)
