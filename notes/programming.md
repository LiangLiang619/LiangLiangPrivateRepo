# 📚 编程

> 共 1 条笔记 · 最后同步：2026-04-24

---

## ⭐️⭐️⭐️ 必掌握 【示例】C++ 虚函数表（vtable）原理

**来源**：学习 · **创建**：2026-04-22 · #C++ #设计模式

> 每个含虚函数的类有一张 vtable，对象头部存 vptr 指针，虚函数调用通过 vptr 间接跳转，实现运行时多态。

## 📌 核心概念
- 每个含虚函数的类拥有一张 虚函数表（vtable）
- 每个对象头部存一个 vptr 指针，指向所属类的 vtable
- 虚函数调用 = 找 vptr → 查 vtable → 跳转，开销约 1 次间接寻址
## 💻 代码示例
```c++
class Base { public: virtual void foo(); };\nclass Derived : public Base { public: void foo() override; };\n\nBase* p = new Derived();\np->foo(); // 运行时调用 Derived::foo
```
## ⚠️ 注意事项
- 析构函数在基类中应声明为 virtual，否则 delete 基类指针时子类析构不会被调用
- final 关键字可阻止类被继承或虚函数被覆盖，编译器可优化为直接调用（devirtualization）

---
