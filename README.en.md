# Fairy-Tale Castle 01

Language: [中文](README.md) | English

Current stage: `FINISHING`; current revision: `revision 11`.

This case was completed with **DeepSeek V4.1 Flash**. Planning, visual understanding, geometric reasoning, and repair capabilities differ between models, so other models may produce different or better results.

## Current Result

![Whole-building assembly contact sheet](assets/preview/assembly/castle_assembly_contact_sheet.jpg)

The main facade has been widened to **11.4 m**. Key quantities are audited separately by elevation and floor: the ground floor of the front elevation has **three windows** and skips the door axis, while the upper floor has **four windows**, including one above the door axis. After widening, the round tower on the left regains reliable contact with the wall while maintaining clearance from every window group.

![Attic roof junction, front vines, and complete assembly](assets/preview/process/attic_window_junction_revision11.jpg)

The current assembly contains 40 component instances, including 21 main window instances, three climbing-vine modules, and one entrance planter. Per-instance front-view silhouette masks cover all 40 instances. There are no unexplained overlaps between the round tower and windows or between wall lanterns and window frames.

![Per-component front-view silhouette audit](assets/preview/assembly/front_component_visibility_overlay.jpg)

## Attic Volume, Roof, and Front Vegetation

The paired attic windows form the front face of a small enclosed dormer volume rather than standing alone as window planes. Behind the windows are a front wall, a floor slab, and left and right side walls. The side walls now use **triangular sections** that taper along the main roof pitch, and the floor slab terminates at the roof intersection. The front edge of the small roof is set back **0.09 m** from the main eave, while its rear edge remains embedded in the main roof, eliminating the exposed vertical wall end formerly visible in side views.

All three vine modules have been repositioned onto the left front tower, the ground-floor wall pier between windows, and the right front wall pier. Each has a visible front elevation silhouette. The two stone chimneys retain their stone shafts and caps, with zero black metal flues on top.

## Color and Surface

The roof retains its approved dark warm charcoal color and uses the flat slate Color, NormalGL, and Roughness maps from Poly Haven `roof_slates_02`. In the current render and reference sampling, the roof's mean green-channel error is 1.1 and its hue error is 0.0139, both within the recorded tolerances.

![Complete final model render](assets/preview/assembly/castle_assembly_hero_three_quarter.png)

## Reference Basis

![Original source ten-view contact sheet](assets/preview/concepts/source_ten_view_contact_sheet_v11.jpg)

The image above contains the user-supplied original ten-view source material, not renders regenerated from the reference model. It was assembled from the original-view copies under the project's `assets/raw/` directory, allowing direct traceability between the input problems and the final assembly. Fixed views derived from the reference model are retained only as process-audit material under `assets/preview/reference/`.

Original concept views and generation-input crops are stored only under `assets/raw/`. Reference views, component QA, whole-building renders, and concise process comparisons are stored only under `assets/preview/`. When the same image is shared by the README and an audit record, it is referenced through relative paths rather than duplicated.

## Advantages of the Skill Workflow

- **Parametric batch changes:** Wall widths, floor heights, openings, window grids, roof pitches, and component arrays are controlled by contract parameters. Changing the building width or standardizing a window type rebuilds the affected components and audits in batches instead of regenerating each component individually.
- **Component asset reuse:** Doors, windows, railings, moldings, chimneys, and vegetation enter the component library through shared interfaces and materials. Later buildings can recombine these assets while preserving a consistent style across different elevations, massing, and layouts.
- **Less repeated AI 3D generation:** Rule-based structures, windows, doors, and repeated attachments favor parametric construction or reusable assets. AI 3D is reserved primarily for organic or sculpted pieces that are difficult to parameterize, avoiding a full 3D regeneration for every building.

## Current Limitations

The model is not yet a final production-grade asset. Some railing connections and detail rhythms remain simplified, and the continuity of local stonework and moldings, along with surface detail at extreme close range, can be refined further. The README reflects the actual state of the current revision and does not describe unfinished construction details as complete.

## Project Structure

```text
components/   17 final components, each with one .blend and one .glb
assembly/     whole-building .blend, deliverable .glb, and current five-view render
reference/    3D reference model and structured records
assets/
  raw/        original concept views and generation inputs
  preview/    reference views, component QA, assembly QA, and selected process images
concepts/     concept prompts and review records
internal/     dimensional contracts, parametric contracts, audits, and migration records
textures/     shared PBR textures
scripts/      reproducible generation and audit scripts for the current revision
```

Seven component source files affected by the facade widening were rebuilt from the verified assembly geometry. The attic-window component is now at revision 7, while the whole-building assembly, README, and GLB all belong to revision 11.

## Deliverables

- [Whole-building Blender source file](assembly/castle_assembly.blend)
- [Whole-building GLB](assembly/fairy_tale_castle_01.glb)
- [Component library index](components/README.md)
- [Current assembly report](assets/preview/assembly/assembly_report.json)
- [Front-view component audit](internal/assembly_front_visibility_audit.json)
- [Key quantity audit](internal/quantity_audit_v11.json)
- [Quantity gate result](internal/quantity_census_audit.json)
- [Host connection and rear-volume audit](internal/attachment_integrity_audit_v11.json)
- [Original ten-view input audit](internal/source_ten_view_input_audit_v11.json)
- [Facade opening contract](internal/wall_openings_v2.json)
- [Directory cleanup record](internal/media_structure_v11.json)

## Next Step

The current revision has passed the quantity matrix, host-connection, scene, parametric-contract, component-source, export/import, front-view occlusion, and material gates. The next stage is user `REVIEW`; `COMPLETE` follows only after user approval.
