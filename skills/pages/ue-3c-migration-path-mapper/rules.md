# 3C 迁移路径映射——详细分类规则

## 1. 3C 分类规则

### Phase 1: 路径关键字匹配（classify_assets.py 内置）

按以下顺序逐条匹配 `外部资产完整路径`，**先命中先采用**。匹配使用大小写不敏感的正则。

#### Camera

```
/Camera/
/CineCamera
_Camera(?![A-Za-z])      # _Camera 后不接字母，防止误匹配 _CameraRig 类
Camera_
/CCM_
BP_Camera
(?:^|/)Camera[A-Z]       # 文件名以 Camera 开头（如 CameraHighAdjustCurve）
```

#### Controller

```
/Controller/
/PlayerController/
/AIController/
(?:^|/)PC_               # 文件名以 PC_ 开头
(?:^|/)AIC_              # 文件名以 AIC_ 开头
BP_Controller
BP_PlayerController
BP_AIController
```

#### Character

```
/Characters?/            # /Character/ 或 /Characters/
/Anim                    # 覆盖 /Animation/, /AnimBP/, /Anim/
/Skeleton/
/Mesh/SK_                # SkeletalMesh 角色资源
(?:^|/)BP_CH_            # 角色蓝图命名
(?:^|/)ABP_CH_           # 角色动画蓝图
(?:^|/)AS_CH_            # 角色动画序列
(?:^|/)AM_CH_            # 角色动画蒙太奇
(?:^|/)SK_               # 骨骼网格体
(?:^|/)BU_               # Body Upper
(?:^|/)OG_               # 外观
(?:^|/)PL_               # Placeholder/Player角色
/AnimCompressSettings/
/AnimNotif               # AnimNotify / AnimNotifyState
/FootPrint/              # 角色脚印
/BlendSpace
/BS_CH_
BP_\w*Char\w*Component   # BP_*Char*Component（角色组件命名约定）
BP_MoeChar               # BP_MoeChar*（角色状态/组件）
BP_MainChar              # BP_MainChar*（主角色组件）
```

### Phase 2: uasset-analyzer 父类推断

路径关键字未命中时，agent 调用 `uasset_exports` + `uasset_imports` 获取资产的 class_name 和父类。

#### class_name / 父类 → 3C 映射

| 匹配关键字（class_name 或 import 中的父类） | 3C 分类 |
|---|---|
| `Character`, `Pawn`, `APawn`, `ACharacter` | Character |
| `AnimInstance`, `AnimBlueprint`, `AnimNotify`, `AnimNotifyState` | Character |
| `SkeletalMesh`, `Skeleton`, `PhysicsAsset` | Character |
| `CameraActor`, `CineCamera`, `CameraComponent`, `CameraShake`, `CameraModifier` | Camera |
| `PlayerController`, `AIController`, `AController`, `APlayerController`, `AAIController` | Controller |
| `PlayerInput`, `InputComponent`, `EnhancedInputComponent` | Controller |
| `ActorComponent`, `SceneComponent` | 需结合组件所属上下文判断——默认 `[待确认]` |

#### 特殊 asset_class 的 3C 默认归属

| asset_class | 默认 3C |
|---|---|
| `AnimSequence`, `AnimMontage`, `AnimComposite` | Character |
| `BlendSpace`, `BlendSpace1D`, `AimOffsetBlendSpace` | Character |
| `Skeleton`, `PhysicsAsset` | Character |
| `AnimBoneCompressionSettings`, `AnimCurveCompressionSettings` | Character |
| `CurveFloat`, `CurveVector`（名称含 Camera/Cam） | Camera |
| `CurveFloat`, `CurveVector`（其他） | `[待确认]` |

### Phase 3: 兜底

以上均不命中 → `3C仓库目标路径` 填 `[待确认]`。

## 2. 子目录规则

确定 3C 分类后，按以下优先级决定子目录。

### 优先级 1: Components/

class_name 或父类继承链中包含以下任一：

```
ActorComponent, SceneComponent, PrimitiveComponent,
MeshComponent, SkeletalMeshComponent, StaticMeshComponent,
AudioComponent, WidgetComponent, CapsuleComponent,
SpringArmComponent, MovementComponent, CharacterMovementComponent,
CameraComponent
```

→ 子目录 = `Components/`

### 优先级 2: Animation/<asset_class>/（仅 3C=Character 时生效）

按精确 asset_class 进一步细分二级目录，便于按类型管理。

| asset_class | 二级目录 |
|---|---|
| `AnimBlueprint` / `AnimBlueprintGeneratedClass` / `AnimLinkedInstance` | `Animation/AnimBlueprint/` |
| `AnimNotify` / `AnimNotifyState` | `Animation/AnimNotify/` |
| `AnimSequence` | `Animation/AnimSequence/` |
| `AnimMontage` | `Animation/AnimMontage/` |
| `AnimComposite` | `Animation/AnimComposite/` |
| `BlendSpace` / `BlendSpace1D` / `AimOffsetBlendSpace` | `Animation/BlendSpace/` |
| `Skeleton` | `Animation/Skeleton/` |
| `PhysicsAsset` | `Animation/PhysicsAsset/` |
| `AnimBoneCompressionSettings` / `AnimCurveCompressionSettings` | `Animation/CompressionSettings/` |
| 其他动画类（兜底） | `Animation/Misc/` |

> 命名约定回退：若无法获取精确 class，按文件名前缀回退（`ABP_*`→AnimBlueprint, `AS_*`→AnimSequence, `AM_*`→AnimMontage, `BS_*`→BlendSpace, `ALI_*`→AnimBlueprint, `AnimNotify*`→AnimNotify）。

### 优先级 3: Config/（统一配置子目录）

asset_class 属于以下集合：

```
DataTable, DataAsset, CurveTable, CurveFloat, CurveVector,
CurveLinearColor, PrimaryDataAsset, CompositeDataTable
```

以及任何 DataAsset 子类（exports 中 class 名含 `DataAsset`）。

→ 子目录 = `Config/`

> 历史曾使用 `ConfigData/`、`Curves/`，**已统一为 `Config/`**。新迁移一律采用 `Config/`；存量已迁的 `ConfigData/`、`Curves/` 视情况合并。

### 优先级 4: 按 asset_class 命名

以上均不匹配，子目录 = `<asset_class>/`。

常见映射示例：

| asset_class | 子目录 |
|---|---|
| `Blueprint` / `BlueprintGeneratedClass` | `Blueprint/` |
| `WidgetBlueprint` | `WidgetBlueprint/` |
| `Material` | `Material/` |
| `MaterialInstance` / `MaterialInstanceConstant` | `MaterialInstance/` |
| `MaterialFunction` / `MaterialFunctionInterface` | `MaterialFunction/` |
| `Texture2D` / `TextureCube` | `Texture/` |
| `StaticMesh` | `StaticMesh/` |
| `SkeletalMesh` | `SkeletalMesh/` |
| `ParticleSystem` / `NiagaraSystem` / `NiagaraEmitter` | `Effect/` |
| `SoundWave` / `SoundCue` | `Sound/` |

> **合并规则**：`MaterialInstanceConstant` → `MaterialInstance/`；`Texture2D`/`TextureCube`/`TextureRenderTarget2D` → `Texture/`；Niagara/Cascade → `Effect/`。

## 3. 边界 Case

| 场景 | 处理 |
|---|---|
| 路径同时匹配多个 C 关键字（如 `/Camera/Character/`） | 取第一个匹配（Camera > Controller > Character） |
| asset_class 为空或无法获取 | 子目录 = `Unknown/` |
| 资产 .uasset 文件磁盘不存在 | 仅依赖路径关键字；子目录回退到路径中最后一级目录名 |
| UE 路径不以 `/Game/` 开头 | 尝试修正（去 `Content/` 前缀加 `/Game/`），失败则标 `[待确认]` |

## 4. asset_class 推断方法

### 从路径关键字推断（无需 MCP）

| 路径特征 | 推断 asset_class |
|---|---|
| 文件名以 `ABP_` 开头 | `AnimBlueprint` |
| 文件名以 `AS_` 开头 | `AnimSequence` |
| 文件名以 `AM_` 开头 | `AnimMontage` |
| 文件名以 `BS_` 开头 | `BlendSpace` |
| 文件名以 `BP_` 开头 | `Blueprint` |
| 文件名以 `SK_` 开头且路径含 `/Mesh/` | `SkeletalMesh` |
| 文件名以 `SM_` 开头且路径含 `/Mesh/` | `StaticMesh` |
| 文件名以 `MI_` 开头 | `MaterialInstance` |
| 文件名以 `M_` 开头（排除 MI_/MF_） | `Material` |
| 文件名以 `MF_` 开头 | `MaterialFunction` |
| 文件名以 `T_` 开头 | `Texture` |
| 文件名以 `FX_` 开头 | `Effect` |
| 路径含 `/AnimCompressSettings/` | `AnimBoneCompressionSettings` |
| 路径含 `AnimNotify` | `AnimNotify` |
| 文件名以 `ALI_` 开头 | `AnimLinkedInstance` → asset_class = `AnimBlueprint` |

### 从 uasset_exports 获取（MCP 调用）

主导出对象的 `class_name` 字段即为精确 asset_class。
