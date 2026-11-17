# Scene Kit

Language: [中文](README.md) | English

**An auditable, component-based and parametric 3D scene workflow for Blender.**

Scene Kit is a 3D workflow skill, not a fixed model pack and not a one-shot modeling prompt. It organizes the journey from concept to delivery into a reusable, parametric, version-audited process. The method itself is subject-agnostic; buildings, blocks, and other whole-scene assemblies are currently its main application area.

> **Input:** concept images, original multi-view references, dimensional and style constraints.
>
> **Output:** decomposable, reusable, reproducible, and auditable Blender components and complete assemblies.

Scene Kit can work with Blender, parametric generators, and optional AI 3D providers. Those models are execution tools. Long-term efficiency and quality come from component contracts, parameter propagation, asset reuse, and evidence-based gates.

![Bilingual Scene Kit workflow illustration](assets/scene-kit-workflow-bilingual.png)

<sub>[Chinese full-size diagram](assets/scene-kit-workflow-zh.png) · [English full-size diagram](assets/scene-kit-workflow-en.png)</sub>

## 1. What Scene Kit Is

The recurring problems in component-based 3D projects are usually not that "one component is not attractive enough," but that the process lacks constraints. Typical examples:

- References are understood, yet attached parts or decorative details are missed during decomposition (for example chimneys, brackets, or roof attachments on a building).
- A dimension or style parameter changes, but related components and the assembly do not follow.
- Repeated components are regenerated every time instead of accumulating into an asset library.
- Something looks correct from the front, but another view reveals missing thickness, rear enclosure, or support.
- Final screenshots and QA no longer belong to the current model, yet old evidence keeps being used.

Scene Kit turns these problems into executable data and audits:

- The reference model only establishes spatial context. It is one baseline in the process and never replaces original source material.
- Every component has a contract for interfaces, parameters, materials, source output, and current QA.
- Parameter changes produce a new build fingerprint; old geometry, screenshots, and audits become invalid immediately.
- Approved components can be reused across projects and gradually accumulate into a component library.
- Rework feeds back into the quantity inventory, contracts, component sources, and assembly.
- Organic modules (for example vines, planters, flower clusters, shrubs, and other vegetation) pass one organic-quality gate; stick stems with flat placeholder leaves are rejected.

## 2. Core Workflow

![Scene Kit core workflow](assets/scene-kit-core-workflow.png)

### 2.1 Concept and fixed reference

Freeze the design language, key dimensions, and a canonical set of multi-view references (for example ten views) first. The reference model then produces fixed views from one shared center, orthographic scale, and resolution to verify massing, depth, occlusion, and attachments. Original source views remain distinct and are never replaced by derived renders.

### 2.2 Quantities before geometry

Before modeling, complete a three-level inventory of macro components, repeated modules, and attachment details, with counts grouped by location (for example windows and doors counted by elevation and floor, and roof or chimney types counted separately). Do not enter batch modeling until the quantities are confirmed.

### 2.3 Component contracts

Every component defines at least three layers of constraints:

- `locked`: openings, interfaces, thickness, origin, orientation, and contact surfaces.
- `guided`: massing silhouette, formal language, material tendency, and period style.
- `free`: ornaments, window patterns, foliage distribution, and other generator-controlled details.

The contract also records implementation route, editable parameters, output files, material bindings, and the current build fingerprint. A component becomes a traceable, replaceable, reusable asset instead of a disposable AI result.

### 2.4 Generation and assembly

Rule-based components (for example wall segments, slabs, windows, doors, railings, and steps) favor parametric generation or existing assets. Organic sculptures and vegetation may use AI 3D. Components are normalized in scale, origin, and interface before assembly, then the standalone sources and the assembly are compared for consistency.

Taking vegetation as an example, every source — procedural, AI-generated, or library — must meet the same organic standard: curved tapered stems, hierarchical branching, dense leaves or flower clusters, natural tone variation, terminal buds, and an irregular silhouette, reviewed through the same multi-view semantic checks. Open-shell leaf boundaries are allowed; floating leaves, wire edges, and zero-area faces are not.

### 2.5 Finishing and acceptance

Assembly is not delivery. Continue checking surfaces, normals, seams, intersections, supports, materials, texture projection, and construction logic, then re-render the current revision's overall views, key close-ups, and reference comparisons.

## 3. Why the Method Works

- **Parametric bulk edits:** dimensions, openings, component groups, and arrays are controlled by contract parameters; one adjustment rebuilds in bulk and reruns the audits.
- **Reusable component assets:** approved components can be recombined to avoid repeated modeling and AI 3D generation (for example windows, moldings, railings, roofing, and vegetation modules).
- **Reusable organic quality:** with vegetation as the reference case, procedural and AI assets share one semantic acceptance bar, so approved modules drop straight into later projects.
- **Traceable quality:** every conclusion is backed by quantity, geometry, material, mask, host-connection, or export evidence rather than "looks about right."
- **Controlled rework cost:** problems are traced to a specific component and revision instead of discarding the whole model.
- **Built for iteration:** well-defined parts stay stable and reusable; uncertain form stays inside local free zones.

## 4. Quality Gates

| Common problem | How Scene Kit checks it |
|---|---|
| Incomplete component inventory | Three-level inventory (macro, repeated, attached), with every item linked to a real component |
| Drifting counts of repeated components | Quantity audit, parametric contracts, and live assembly instances cross-checked together |
| Front-only parts with no thickness or mounting surface | Side walls, rear panels, volume, projection depth, and host contact checks |
| Attachments overshooting or failing to cover their host | Setback distance, rear coverage, and real intersection with the host surface |
| Components occluding each other | Live component masks, projected overlap, and front-to-back depth audits |
| Matching color but wrong material identity | Material semantics, texture scale, normals, roughness, and projection checked separately |
| Standalone component inconsistent with the assembly | Bounding boxes, object counts, triangles, origins, and material bindings compared |
| Stale screenshots or approvals still in use | Revision, parameter fingerprint, file hashes, and current QA bound together |

## 5. Detail-Recognition Enhancements

The fixed multi-view set remains the mandatory primary reference and the `analysis_ready` gate. When a local feature remains unclear (for example seams, an occluded back side, component depth, connection details, or repeated counts), temporary close-up or oblique diagnostic views can be captured from the same normalized reference model.

These supplementary views support recognition and cross-confirmation only. They never replace or reorder the fixed view set and are not required in the final project; any conclusion drawn from them must still be cross-validated against the fixed views or original sources. Components attached to a host surface also pass a dedicated attachment gate: real volume, side and rear structure, projection depth, and a reliable connection to the host.

## 6. Case Study: Fairy-Tale Castle 01

The case below shows how the method applies to a real building. Its specific style, component counts, and roof forms are examples, not fixed Scene Kit rules.

The main facade is **11.4 m** wide and the assembly contains **40 component instances**, including 21 main windows, three climbing-vine modules, and one entrance planter. Per-instance front silhouettes cover all 40 instances, with no tower/window or unexplained cross-component overlaps.

![Whole-building five-view contact sheet](assets/preview/assembly/castle_assembly_contact_sheet.jpg)

### 6.1 Starting from the original ten views

![User-supplied original ten-view material](assets/preview/concepts/source_ten_view_contact_sheet_v11.jpg)

These ten views are the user-supplied source input, not renders regenerated from the reference model. They establish the reference model, component boundaries and counts, material checks, and occlusion review. Derived views remain process-audit evidence only.

### 6.2 Roof-to-wall rework

The paired attic windows belong to a real enclosed dormer volume. Both cheeks use **triangular sections** that taper along the main roof pitch, and the floor stops at the roof intersection. The small roof front is set back **0.09 m** from the main eave, while its rear edge remains embedded in the main roof.

### 6.3 Component examples

The round tower and climbing vines are not inseparable parts of the final model. Each is a component asset with its own source, parametric contract, material bindings, and QA. Approved components are assembled into the building and can be reused in later projects through the same interfaces.

| Round corner tower | Climbing vine |
|:---:|:---:|
| <img src="assets/preview/components/round_corner_tower/round_corner_tower_v3_three_quarter.png" width="100%" alt="Standalone round tower component"> | <img src="assets/preview/components/climbing_vine_module/climbing_vine_module_v2_three_quarter.png" width="100%" alt="Standalone climbing vine component"> |
| Independent tower body, cap, and windows | Reusable instantiated vine module |

### 6.4 Components and front-view occlusion

![Per-component front silhouette audit](assets/preview/assembly/front_component_visibility_overlay.jpg)

The 21 main windows are audited by elevation and floor: three on the ground-floor front elevation with the door axis skipped, and four on the upper floor including the centered door-axis window. The tower, window groups, wall lantern, vines, and chimneys pass the live-instance and silhouette checks for the current assembly.

### 6.5 Color and surface

The roof uses a dark warm-charcoal flat slate and the Color, NormalGL, and Roughness maps from Poly Haven `roof_slates_02`. The current render has a mean green-channel error of **1.1** and a hue error of **0.0139** against the recorded reference samples.

### 6.6 Case Deliverable Scope

The case delivers the whole-building Blender source, whole-building GLB, a 17-component library index, the current assembly report, front-view component audit, key quantity audit, quantity gate result, host-connection and rear-volume audit, original ten-view input audit, and facade opening contract.

## 7. Install and Quick Start

Copy the `scene-kit/` folder into the skill directory supported by your host.

```powershell
Copy-Item .\scene-kit "$HOME\.codex\skills\scene-kit" -Recurse
```

```bash
python scene-kit/scripts/scene_kit.py init ./my-scene --name "Garden Villa"
python scene-kit/scripts/scene_kit.py prompts ./my-scene
python scene-kit/scripts/scene_kit.py validate ./my-scene
```

See [INSTALL.md](INSTALL.md) for installation, commands, and migration guidance. The main skill entry point is [scene-kit/SKILL.md](scene-kit/SKILL.md).

## 8. Repository Layout

```text
README.md / README.en.md   unified GitHub entry points
INSTALL.md                 installation and command reference
scene-kit/                 Scene Kit skill
scene-kit.standalone.md    single-file rule variant
assembly/                  case-study Blender and GLB files
components/                case component index and QA; standalone component binaries remain in the full project workspace
assets/                    workflow diagrams, plus case references, QA, and current renders (previews under assets/preview/)
internal/                  current quantity, opening, host, and acceptance audits
```

## 9. Limitations and License

The example is not a final production-grade asset. Some railing connections, post spacing, local stonework, and molding continuity remain simplified, and extreme close-up surface detail can be refined further. The README reflects the current assembly state.

- Runtime: Python 3.10+, Blender, and an optional AI 3D provider
- Supported hosts: Codex, Claude Code, Trae, and similar skill hosts
- This repository does not currently grant a license. Add an appropriate license before public redistribution.

## 10. Final Result

![Final result of Fairy-Tale Castle 01](assets/preview/assembly/castle_assembly_final_full.png)
