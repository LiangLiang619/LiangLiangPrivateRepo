---
title: "C++ 虚函数学习笔记（结合 UE 项目实例 & Java 对比）"
category: "编程"
tags:
  - "C++"
  - "UE5"
  - "设计模式"
source: "学习"
importance: 3
importance_label: "⭐️⭐️⭐️"
summary: "虚函数核心作用是实现多态，通过基类指针/引用调用函数时根据实际对象类型执行对应版本。涵盖 virtual/override/纯虚函数/final 关键字，UE 相机系统和状态机实战案例，以及 C++ 与 Java 多态机制的详细对比。"
created: 2026-05-07
updated: 2026-05-07
notion_url: "https://www.notion.so/C-UE-Java-3595f1d3510d8172b43deac5136341a6"
---

# C++ 虚函数学习笔记（结合 UE 项目实例 & Java 对比）

> **分类**：编程 | **来源**：学习 | **重要程度**：⭐️⭐️⭐️
>
> 虚函数核心作用是实现多态，通过基类指针/引用调用函数时根据实际对象类型执行对应版本。涵盖 virtual/override/纯虚函数/final 关键字，UE 相机系统和状态机实战案例，以及 C++ 与 Java 多态机制的详细对比。

## 📌 核心概念

- 虚函数的核心作用是实现多态（Polymorphism）——通过基类指针/引用调用函数时，根据实际对象类型执行对应版本

- 关键字：virtual（声明可重写）、override（子类重写标记）、= 0（纯虚函数）、final（禁止继续重写）、Super::（UE调用父类）

- C++ 多态只在指针/引用上生效；Java 默认所有方法都是虚函数

- UE 项目实例：相机系统继承链（AMoeCameraBase → AMoeCameraMainPlayer）、状态机多态（UMoeStateBase*）

## 💻 代码示例

```c++
// 基类声明虚函数
virtual void TickCamera(float DeltaTime);
virtual bool IsNpcCharacter() { return false; }  // 带默认实现

// 子类重写
void AMoeCameraMainPlayer::OnBeginPlay() override {
    InitProcessorData();
    Super::OnBeginPlay();  // 调用父类
}

// 多态生效条件
AMoeCameraBase* camera = new AMoeCameraMainPlayer();
camera->TickCamera(dt);  // OK 多态生效

// 对象切片（多态失效！）
AMoeCameraBase camera = AMoeCameraMainPlayer();  // 子类部分被切掉
```

## ⚠️ 注意事项

- 忘写 virtual → 没有多态，函数按指针类型静态绑定

- 对象切片 → 用值而非指针/引用持有对象，子类部分被切掉

- 忘写 override → 签名写错时不报错，变成全新函数而非重写

- 析构函数非虚 → 通过基类指针 delete 子类对象会内存泄漏（UE UObject 已处理）

- C++ 接口 = 纯虚类 + 多继承，UE 约定接口名以 I 开头

---

**一句话总结：Java 把多态做成默认行为；C++ 把多态做成可选行为，需要 virtual 明确表达意图，且只在指针/引用上生效。**

