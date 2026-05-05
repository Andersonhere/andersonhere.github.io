---
title: memcpy与虚函数表：vptr内存布局解析
tags: [C++, 内存, 虚函数, 继承, 面试]
created: 2026-05-05 00:15:00
updated: 2026-05-05 00:15:00
source: https://mp.weixin.qq.com/s/r9ssVVPXs22GGLmdGaQVuw
author: C加加滴神
---

# memcpy与虚函数表：vptr内存布局解析

看这段代码：

```cpp
class Base {
public:
    virtual void speak() { std::cout << "Base" << std::endl; }
    int value = 42;
};

class Derived : public Base {
public:
    void speak() override { std::cout << "Derived" << std::endl; }
    int extra = 99;
};

int main() {
    Derived d;
    Base b;
    std::memcpy(&b, &d, sizeof(Base));
    b.speak();  // 输出什么？
}
```

`b.speak()` 输出 `"Base"` 还是 `"Derived"`？

标准的回答是：**未定义行为，什么都可能发生。** 但你拿 GCC 或 Clang 跑一下，大概率输出 `"Derived"`——`memcpy` 把 `d` 的 vptr 原封不动搬到了 `b` 身上，`b` 以为自己是个 `Derived`。

这还是最温和的炸法。真正的坑藏在多继承、虚析构、跨模块的场景里，那时候你连 segfault 的堆栈都看不懂。

这篇拆一件事：**memcpy 到底动了对象内存里的哪块禁区，为什么编译器和标准都不让你碰。** 从 vptr 的位置、vtable 的结构、多继承下的双 vptr 布局，到构造过程中 vptr 的逐层覆写，只讲内存层面到底发生了什么。

## vptr 住在对象的什么位置

要搞懂 memcpy 为什么能闯祸，先得知道 vptr 在哪。

一个含虚函数的类，编译器会在对象内存里塞一个隐藏指针。你在代码里看不到它，但它实实在在占了 8 个字节（64 位系统下），而且绝大多数编译器把它放在对象的最前面。

拿前面那个 `Base` 来说，它在内存里长这样：

```
Base 对象（16 字节）：
┌──────────────────────┐
│  vptr (8 bytes)       │ → 指向 Base::vtable
├──────────────────────┤
│  value (4 bytes)      │ = 42
├──────────────────────┤
│  padding (4 bytes)    │
└──────────────────────┘
```

`Derived` 继承了 `Base`，内存布局就是在 `Base` 后面接着拼自己的成员：

```
Derived 对象（24 字节）：
┌──────────────────────┐
│  vptr (8 bytes)       │ → 指向 Derived::vtable
├──────────────────────┤
│  value (4 bytes)      │ = 42
├──────────────────────┤
│  extra (4 bytes)      │ = 99
├──────────────────────┤
│  padding (8 bytes)    │
└──────────────────────┘
```

盯住 vptr 那一行。`Base` 对象的 vptr 指向 `Base::vtable`，`Derived` 对象的 vptr 指向 `Derived::vtable`。不是同一张表。

编译器在构造函数里把 vptr 设成正确的值——先跑 `Base` 的构造函数，vptr 指向 `Base::vtable`；然后 `Derived` 的构造函数执行完，vptr 被改写成 `Derived::vtable`。这个过程保证了一件事：**对象在任何时刻，通过 vptr 找到的 vtable，都对应它当前的真实类型。**

`memcpy` 打破的就是这个保证。

## memcpy 到底覆盖了什么

回到开头那段代码。`std::memcpy(&b, &d, sizeof(Base))` 做的事情很简单：从 `&d` 开始，拿 16 个字节，逐字节搬到 `&b`。

`Derived` 对象的前 16 个字节是什么？vptr（8 字节）+ value（4 字节）+ padding（4 字节）。

memcpy 不知道前 8 个字节是编译器注入的隐藏指针，它只管搬。搬完之后，`b` 的 vptr 不再指向 `Base::vtable`——被 `d` 的 vptr 盖掉了，现在指向 `Derived::vtable`。

```
memcpy 前：
  b.vptr → Base::vtable      { &Base::speak }
  d.vptr → Derived::vtable   { &Derived::speak }

memcpy 后：
  b.vptr → Derived::vtable   { &Derived::speak }
  d.vptr → Derived::vtable   { &Derived::speak }（没变）
```

调 `b.speak()` 的时候，编译器走的路径是：读 `b.vptr` → 查 vtable → 拿到 `Derived::speak` 的地址 → 调用。一个 `Base` 类型的栈上对象，跑了 `Derived` 的虚函数。

这个例子里它碰巧还能跑，因为 `Derived::speak()` 没有访问 `Derived` 独有的成员。但如果 `Derived::speak()` 里面读了 `extra` 呢？`b` 是个 `Base`，它的内存里根本没有 `extra`。你读到的要么是 padding 的垃圾值，要么直接越界读进了相邻变量的地盘。

往更危险的方向想——虚析构函数。`delete` 一个被 memcpy 篡改过 vptr 的对象，编译器会通过 vptr 去调错误类型的析构函数，释放错误的内存块。double free 或者 heap corruption，取决于你的运气好不好。

## 单继承下 vtable 长什么样

你可能会想：两个 vtable 里的函数签名都一样，vptr 指错了也不一定会炸吧？

不行。因为 vtable 不只存虚函数地址，它还藏了别的东西。

看一个更贴近实际的例子：

```cpp
class Animal {
public:
    virtual void speak() = 0;
    virtual void eat() { std::cout << "eating" << std::endl; }
    virtual ~Animal() = default;
    int age = 0;
};

class Dog : public Animal {
public:
    void speak() override { std::cout << "woof" << std::endl; }
    ~Dog() override { /* 释放 Dog 独有资源 */ }
    std::string name;
};
```

编译器给 `Animal` 和 `Dog` 各生一张 vtable。在 Itanium C++ ABI（GCC 和 Clang 用的 ABI）下，vtable 的结构大致长这样：

```
Animal::vtable:
  [offset_to_top = 0]
  [typeinfo → Animal]
  [slot 0] → __cxa_pure_virtual   (Animal::speak 是纯虚函数)
  [slot 1] → Animal::eat()
  [slot 2] → Animal::~Animal()    (complete destructor)
  [slot 3] → Animal::~Animal()    (deleting destructor)

Dog::vtable:
  [offset_to_top = 0]
  [typeinfo → Dog]
  [slot 0] → Dog::speak()
  [slot 1] → Animal::eat()        (没 override，继承原地址)
  [slot 2] → Dog::~Dog()          (complete destructor)
  [slot 3] → Dog::~Dog()          (deleting destructor)
```

vtable 前面有两个隐藏字段。`offset_to_top` 在单继承下永远是 0，在多继承下会变成非零值，后面会讲。`typeinfo` 就是 RTTI 信息，`dynamic_cast` 和 `typeid` 靠它做运行时类型判断。

注意 Itanium ABI 给每个类生成了两个析构函数版本：complete destructor（析构对象和基类部分，不释放内存）和 deleting destructor（先调 complete destructor 再调 `operator delete`）。两个版本各占 vtable 的一个 slot。

设想这个场景：你把 `Dog` 对象的 vptr 通过 memcpy 覆盖到了一个栈上的 `Animal` 身上。作用域结束时 `Animal` 析构，编译器通过被篡改的 vptr 去调了 `Dog::~Dog()`——但这个对象只有 `Animal` 的内存空间。`Dog::~Dog()` 里面要析构 `std::string name`，它按照 `Dog` 的布局去偏移 `this` 指针寻址 `name`，读到的地址在 `Animal` 对象的边界之外。栈上某个邻接变量被当成 `std::string` 的内存来析构。crash 是大概率的结果，小概率更糟：沉默的内存污染，直到另一个不相关的地方才爆出来。

## 多继承下的双 vptr 布局

单继承只有一个 vptr，场面还算可控。多继承直接把复杂度拉高一个台阶。

```cpp
class Flyable {
public:
    virtual void fly() { std::cout << "flying" << std::endl; }
    int altitude = 0;
};

class Swimmable {
public:
    virtual void swim() { std::cout << "swimming" << std::endl; }
    int depth = 0;
};

class Duck : public Flyable, public Swimmable {
public:
    void fly() override { std::cout << "duck fly" << std::endl; }
    void swim() override { std::cout << "duck swim" << std::endl; }
    int feathers = 1000;
};
```

`Duck` 继承了两个有虚函数的基类。编译器会在 `Duck` 的内存里放**两个 vptr**：

```
Duck 对象（40 字节）：
┌─────────────────────────┐ offset 0
│  vptr_1 (8 bytes)        │ → Duck 主 vtable（Flyable 部分）
├─────────────────────────┤
│  altitude (4 bytes)      │
├─────────────────────────┤
│  padding (4 bytes)       │
├─────────────────────────┤ offset 16
│  vptr_2 (8 bytes)        │ → Duck 第二 vtable（Swimmable 部分）
├─────────────────────────┤
│  depth (4 bytes)         │
├─────────────────────────┤
│  padding (4 bytes)       │
├─────────────────────────┤ offset 32
│  feathers (4 bytes)      │
├─────────────────────────┤
│  padding (4 bytes)       │
└─────────────────────────┘
```

两个 vptr 分别服务两条继承链。把 `Duck*` 转成 `Flyable*`，指针不动，因为 `Flyable` 子对象在最前面。但把 `Duck*` 转成 `Swimmable*`，编译器会偷偷给指针加一个偏移（16 字节），让它跳到 vptr_2 的位置。这个指针调整（pointer adjustment）是自动发生的，你在代码里感知不到。

但 memcpy 不会做任何指针调整。

考虑这段代码：

```cpp
Duck duck;
Swimmable sw;
std::memcpy(&sw, &duck, sizeof(Swimmable));
```

你可能以为这是在拷贝 duck 的 Swimmable 部分。实际上 `&duck` 指向的是 `Duck` 对象的起始地址——vptr_1 的位置，属于 `Flyable` 子对象的领地。`sizeof(Swimmable)` 大概 16 字节，所以 memcpy 拿走的是 vptr_1 + altitude + padding。跟 Swimmable 一点关系都没有。

`sw` 的 vptr 现在指向 Duck 的主 vtable（Flyable 那张）。调 `sw.swim()` 的时候，编译器按 vtable 偏移去查 slot，查到的可能是 `Duck::fly()` 的地址，也可能是别的完全不相干的函数入口。崩不崩看运气。

就算你"聪明"地做了 `memcpy(&sw, static_cast<Swimmable*>(&duck), sizeof(Swimmable))`，把偏移纠正了呢？vptr_2 和 depth 确实拷对了。但 vptr_2 指向的 vtable 里面，`offset_to_top` 的值是 -16——意思是从 `Swimmable` 子对象的位置往回偏移 16 字节才能回到 `Duck` 对象的起始地址。对一个独立的 `Swimmable` 对象来说，这个 offset 是错的。一旦走到 `dynamic_cast` 或者虚析构函数需要用这个偏移来回溯完整对象的地方，就会读到完全错误的内存。

## 构造过程中 vptr 的逐层覆写

还有一个容易被忽略的点：vptr 不是一锤子设好的，而是构造过程中逐层改写的。

```cpp
class A {
public:
    A() { speak(); }
    virtual void speak() { std::cout << "A" << std::endl; }
};

class B : public A {
public:
    B() { speak(); }
    void speak() override { std::cout << "B" << std::endl; }
};
```

构造 `B` 对象的时候：
- 先进 `A` 的构造函数，vptr 设成 `A::vtable`
- `A()` 里调 `speak()`，走 vptr 查到 `A::speak()`，输出 `"A"`
- `A` 构造完，进 `B` 的构造函数，vptr 被覆写成 `B::vtable`
- `B()` 里调 `speak()`，走 vptr 查到 `B::speak()`，输出 `"B"`

这种逐层覆写保证了一件事：某一层构造函数里调虚函数，只会派发到当前层或更上层的实现，不会调到还没构造完的派生类——标准在 [class.cdtor]/4 里对此有明确定义。

跟 memcpy 的关系是什么？假设你在 `A` 的构造函数里，对 `*this` 做了一次 memcpy 快照（比如写进某个缓冲区），然后等 `B` 构造完之后再把快照 memcpy 回来。你恢复的 vptr 是 `A::vtable` 的地址，但对象已经是一个完整的 `B` 了。后面所有虚函数调用都会被派发到 `A` 的实现，`B` override 的逻辑全部失效。如果 `B` 的析构函数依赖自己的虚函数来释放资源——定时炸弹就埋好了。

## 标准怎么说

从内存角度把机制拆清楚之后，看标准的态度。其实很简单明确。

C++11 引入了 trivially copyable 这个概念（[basic.types]/9）。类型如果满足 trivially copyable，可以安全地用 memcpy 拷贝——标准保证逐字节拷贝和原对象语义等价。

含虚函数的类**一定不是** trivially copyable。判定条件之一就是：不能有虚函数、不能有虚基类。只要出现了 `virtual`，`std::is_trivially_copyable_v` 就是 `false`。

```cpp
static_assert(!std::is_trivially_copyable_v<Base>);
static_assert(!std::is_trivially_copyable_v<Derived>);
```

标准给这个限定不是保守，是因为 vptr 这种编译器注入的隐藏状态，从根本上就不能被当成"普通数据字节"来搬运。memcpy 的契约是"源和目标的字节序列语义等价"，但 vptr 的语义取决于对象的动态类型和内存位置——这些信息不在字节里面。

如果你确实需要做底层的对象复制——比如在自定义内存分配器或对象池里——正确做法是 placement new 加拷贝构造函数：

```cpp
alignas(Dog) unsigned char buf[sizeof(Dog)];
Dog original;
Dog* copy = new (buf) Dog(original);  // vptr 由构造函数正确初始化
// ...
copy->~Dog();  // 用完手动析构
```

## 实际工程里的三个典型翻车场景

### 1. 序列化和反序列化

有些代码为了"效率"直接 memcpy 把对象写进文件或者网络缓冲区，读出来再 memcpy 回来。对 POD 类型这没毛病。但如果对象有虚函数，读回来之后 vptr 指向的地址可能已经变了——ASLR（地址空间布局随机化）每次启动都会打乱代码段地址，上一次运行时的 vtable 地址这次大概率是无效内存。

### 2. 跨动态库边界

同一个类在主程序和 .so/.dll 里可能各有一份 vtable，取决于符号可见性和链接策略。一侧构造对象，另一侧 memcpy 复制，vptr 跨越了模块边界。模块卸载后 vtable 的内存被回收，vptr 变悬挂指针。不一定立刻崩——可能跑了很久之后在一个毫不相关的地方 segfault。

### 3. 对象池的"重置"

为了复用内存，有些对象池把用完的对象 memcpy 回一个"初始模板"的快照。如果这个快照是基类构造阶段拍的，恢复之后 vptr 就是基类的 vtable。后面把这块内存当派生类对象来用，虚函数调用全线错位。正确做法是 placement new 重新构造，不是 memcpy 回写。

## 为什么有人"用了也没崩"

最后说一个常见困惑：既然这么危险，为什么有些代码用了 memcpy 拷贝虚函数对象也没出事？

通常是这几种情况。

### 源和目标类型完全相同，在同一个编译单元同一次运行里

vptr 拷过去指向的还是同一张表。能跑，但你绕过了拷贝构造函数——构造函数里做的初始化逻辑（注册观察者、增加引用计数、初始化互斥锁）全被跳过了。表面没事，实际上状态已经不一致。

### 虚函数实现里没碰派生类成员

vptr 指错了，但调到的函数实现没有通过 `this` 去访问只存在于特定派生类的成员变量，所以没产生可观察的错误。"不崩"和"正确"是两码事——标准定义的未定义行为意味着编译器在优化时可以做任何假设。`-O0` 下能跑的代码，`-O2` 下可能产生完全不同的结果，因为编译器假设你不会写 UB。

### 没有触发虚析构、dynamic_cast 或 typeid

vptr 被篡改了，但始终没有走到需要用 vtable 里的 typeinfo 或 offset_to_top 的路径，那颗雷就一直没踩到。不代表安全，只代表还没爆。

## 总结

一条可执行的判断标准：**`std::is_trivially_copyable_v<T>` 返回 `false`，就不要用 memcpy。** 这是语言层面给你画的安全线。

回到开头那四行：

```cpp
Derived d;
Base b;
std::memcpy(&b, &d, sizeof(Base));
b.speak();
```

现在你看得清楚了：memcpy 把 `d` 的 vptr 搬到了 `b` 的 vptr 位置，`b` 的虚函数分发链从 `Base::vtable` 被篡改成了 `Derived::vtable`。这个例子里碰巧能跑，但只要继承体系稍微复杂一点——多继承、虚析构、跨模块——就是实打实的内存事故。

memcpy 是 C 时代的工具，只认字节。C++ 对象模型比"一块平坦的字节数组"复杂得多：vptr 是编译器注入的隐藏状态，vtable 跟类型绑定，构造函数里的逐层覆写保证了多态调用在每一刻都指向正确的类型实现。这些机制都建立在一个前提上——**vptr 只由构造函数和析构函数管理，其他方式的写入都是越权。**

底层内存管理需要一条规则就够了：**非 trivially copyable 的类型，用构造函数建对象，用拷贝/移动语义复制对象。memcpy 管不了对象模型的事。**

---

> 原文链接：[C加加滴神](https://mp.weixin.qq.com/s/r9ssVVPXs22GGLmdGaQVuw)
