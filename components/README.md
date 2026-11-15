# 最终组件库

共 17 件组件。每件只保留一份最终 Blender 源文件、一份 GLB 和当前 QA 入口；组件源文件不包含整栋参考物或临时调试物。

| 组件 | 类型 | 三角面 | 尺寸 / m | 源文件 | GLB | QA |
|---|---|---:|---|---|---|---|
| `wall_envelope` | castle_wall_envelope | 3010 | 11.40 × 7.50 × 6.00 | `wall_envelope.blend` | `wall_envelope.glb` | [对照图](../assets/preview/components/wall_envelope/wall_envelope_v5_material_comparison.jpg) |
| `floor_slab_system` | floor_slab | 216 | 11.00 × 7.10 × 3.22 | `floor_slab_system.blend` | `floor_slab_system.glb` | [对照图](../assets/preview/components/floor_slab_system/floor_slab_system_v5_material_comparison.jpg) |
| `stone_base_plinth` | stone_base | 1188 | 11.70 × 7.80 × 0.51 | `stone_base_plinth.blend` | `stone_base_plinth.glb` | [对照图](../assets/preview/components/stone_base_plinth/stone_base_plinth_v5_material_comparison.jpg) |
| `main_roof_assembly` | slate_roof | 164 | 12.05 × 8.08 × 3.08 | `main_roof_assembly.blend` | `main_roof_assembly.glb` | [对照图](../assets/preview/components/main_roof_assembly/main_roof_assembly_v5_material_comparison.jpg) |
| `tall_window_assembly` | divided_light_window | 3564 | 1.20 × 0.32 × 1.50 | `tall_window_assembly.blend` | `tall_window_assembly.glb` | [对照图](../assets/preview/components/tall_window_assembly/v5_component_boundary_comparison.jpg) |
| `entrance_portal` | entrance_portal | 792 | 1.18 × 0.32 × 2.26 | `entrance_portal.blend` | `entrance_portal.glb` | [对照图](../assets/preview/components/entrance_portal/entrance_portal_v2_material_comparison.jpg) |
| `stone_facade_trim` | stone_facade_trim | 288 | 11.56 × 7.66 × 2.85 | `stone_facade_trim.blend` | `stone_facade_trim.glb` | [对照图](../assets/preview/components/stone_facade_trim/stone_facade_trim_v5_material_comparison.jpg) |
| `corner_stone_detail` | corner_quoin | 1824 | 11.52 × 7.62 × 5.12 | `corner_stone_detail.blend` | `corner_stone_detail.glb` | [对照图](../assets/preview/components/corner_stone_detail/corner_stone_detail_v5_material_comparison.jpg) |
| `stone_chimney_primary` | stone_chimney | 96 | 两座，单座 0.98 × 0.98 × 2.14 | `stone_chimney_primary.blend` | `stone_chimney_primary.glb` | [对照图](../assets/preview/components/stone_chimney_primary/stone_chimney_primary_v2_material_comparison.jpg) |
| `porch_railing_primary` | wooden_porch_railing | 312 | 3.64 × 0.14 × 0.99 | `porch_railing_primary.blend` | `porch_railing_primary.glb` | [对照图](../assets/preview/components/porch_railing_primary/porch_railing_primary_v1_material_comparison.jpg) |
| `attic_window_assembly` | paired_attic_window | 3228 | 2.30 × 2.24 × 1.33 | `attic_window_assembly.blend` | `attic_window_assembly.glb` | [对照图](../assets/preview/components/attic_window_assembly/attic_window_assembly_v7_material_comparison.jpg) |
| `wooden_entrance_porch` | timber_entrance_porch | 328 | 1.75 × 0.83 × 2.78 | `wooden_entrance_porch.blend` | `wooden_entrance_porch.glb` | [对照图](../assets/preview/components/wooden_entrance_porch/wooden_entrance_porch_v5_material_comparison.jpg) |
| `entrance_steps` | entrance_steps | 72 | 1.80 × 1.04 × 0.51 | `entrance_steps.blend` | `entrance_steps.glb` | [对照图](../assets/preview/components/entrance_steps/entrance_steps_v1_material_comparison.jpg) |
| `wall_lantern_primary` | wall_lantern | 336 | 1.43 × 0.32 × 0.50 | `wall_lantern_primary.blend` | `wall_lantern_primary.glb` | [对照图](../assets/preview/components/wall_lantern_primary/wall_lantern_primary_v5_material_comparison.jpg) |
| `climbing_vine_module` | climbing_vine | 60000 | 0.76 × 0.18 × 1.20 | `climbing_vine_module.blend` | `climbing_vine_module.glb` | [对照图](../assets/preview/components/climbing_vine_module/climbing_vine_module_v2_material_comparison.jpg) |
| `porch_planter_primary` | potted_plant | 2156 | 0.30 × 0.30 × 0.55 | `porch_planter_primary.blend` | `porch_planter_primary.glb` | [对照图](../assets/preview/components/porch_planter_primary/porch_planter_primary_v1_material_comparison.jpg) |
| `round_corner_tower` | round_corner_tower | 2498 | 2.56 × 2.56 × 7.28 | `round_corner_tower.blend` | `round_corner_tower.glb` | [对照图](../assets/preview/components/round_corner_tower/round_corner_tower_v3_material_comparison.jpg) |

## Revision 5–11 更新

墙体、楼板、基座、主屋面、石腰线、转角石和入口壁灯已从 revision 5 整栋装配中的实际对象层级重建为独立源文件。各源文件与整栋使用同一几何、同一材质绑定和同一世界尺寸。

对应的几何与贴图审计位于各自目录的 `geometry_audit_v5.json` 和 `blender_audit_v5.json`。入口壁灯按门轴成对布置，中心位于 `x=-0.56` 与 `x=0.56 m`，避免与右侧一层窗石套相交。

阁楼窗组件已补齐前墙体量、窗间前墙、独立双坡小屋顶和主屋面连接。两侧墙采用沿主屋面坡向收束的三角形截面，底板止于屋面交线；小屋顶前沿退后主檐 0.09 m，后缘埋入主屋面并继续覆盖房体深度。对应审计为 `geometry_audit_v11.json` 和 `blender_audit_v7.json`。石烟囱组件已删除全部黑色金属烟管。

三组藤蔓实例已移动到左前圆塔和两处前立面墙墩，正面遮罩均有可见像素。

组件索引与面数、尺寸和 QA 路径同步记录在 [index.json](index.json)。
