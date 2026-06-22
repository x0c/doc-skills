# Depth Patterns

本文定义 doc-init 深度扫描阶段的知识提取模式。Step 8 扫描完成后、进入 per-域深写前读取本文件。

`scripts/depth_scanner.py` 提供机械提取结果（状态转换、并发锁、事件发布、DSL 格式等原始信号），本文指导模型如何将机械结果转化为 KB 各 section 的内容——机械扫描告诉你「在哪里」，本文告诉你「写什么、写进哪里、易错在哪」。

---

## 7 个通用提取模式

### a) 状态机提取

**适用 KB section**：§2 核心流程 / 状态机

**通用识别信号**：
- 某个实体字段存储当前「阶段」或「状态」，值域有限且有语义
- 存在「只有在 A 状态才能执行 B 操作」的条件校验
- 存在「执行 C 操作后必然变为 D 状态」的写入逻辑
- 存在终态（进入后无法自然变化、只能被特殊操作干预）

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `enum OrderStatus`、`statusEnum`、`BizStatus`、`.eq(status, X)` 查询条件、`Assert.isTrue(entity.getStatus() == X)`、`@PostUpdate` / `@PreUpdate` 钩子 |
| Python | `status = models.CharField(choices=...)`、`@transition(field=status, source=X, target=Y)`（django-fsm）、`if obj.state not in ALLOWED_STATES` |
| TypeScript/JS | `state: 'pending' \| 'active' \| 'closed'`、`xstate` / `robot` machine config、`switch(entity.status)` + throw |
| Go | `const (StatusPending Status = iota ...)`、`if s.state != StateReady { return ErrInvalidState }` |
| C#/.NET | `enum OrderState`、`[Flags]`、`switch(entity.State)` + 异常、Stateless / Appccelerate.StateMachine |

**提取方法**：
1. 收集所有「状态/阶段」枚举或常量（`depth_scanner.py` 的 `status_patterns`）
2. 对每个状态值：grep 它被写入的方法名（= 触发转换的操作）
3. grep 它被读取用于前置校验的位置（= 转换前置条件）
4. 画出：`状态A --[操作]--前置条件--> 状态B`，标注终态
5. 写入 KB §2，用简明列表或表格；附代码索引（类名 + 行号）

**AI 易错点**：不提取状态机时，AI 会在错误的状态下触发操作（如对已注销实体执行冻结），导致数据一致性问题，且这类 bug 只在特定状态流下才会触发。

---

### b) 并发控制识别

**适用 KB section**：§6 隐性约束（**AI 易错点** 标签）

**通用识别信号**：
- 对同一资源的写操作存在乐观锁版本字段（`version`）或显式锁获取
- 存在分布式锁 key 构造（通常是 `"lock:" + entityId`）
- 存在重试逻辑包裹的并发冲突异常捕获
- 存在基于 CAS 的 update（`WHERE version = ?`，更新行数校验）
- 存在幂等写入后再加锁（先加锁后查 + 写的双重检查）

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `@Version`、`OptimisticLockingFailureException`、`redisTemplate.opsForValue().setIfAbsent`、`SELECT FOR UPDATE`、`@Lock(LockModeType.PESSIMISTIC_WRITE)` |
| Python | `select_for_update()`（Django）、`redis.set(key, value, nx=True, ex=ttl)`、`retry_on_conflict`、`__version__`（SQLAlchemy） |
| TypeScript/JS | `$transaction`（Prisma）、`redis.set(key, value, 'NX', 'EX', ttl)`、`mongoose` `__v` 字段、Sequelize `version: true` |
| Go | `sync.Mutex`、`sync.RWMutex`、`singleflight`、`WHERE version = $n` 更新行数检查、Redis `SET NX EX` |
| C#/.NET | `[ConcurrencyCheck]` / `[Timestamp]`（EF）、`IsolationLevel.Serializable`、`StackExchange.Redis.SetAddAsync ... NX` |

**提取方法**：
1. 收集 `depth_scanner.py` 的 `concurrency_patterns`
2. 对每条信号：确认它保护的是哪个实体 / 哪个操作
3. 记录：锁粒度（对象级 / 操作级 / 全局）、锁范围（TTL / 事务边界）、锁 key 构造规则
4. 注明：加锁失败的处理（抛异常 / 重试 / 幂等返回）
5. 写入 KB §6，每条标注 **AI 易错点**

**AI 易错点**：不识别并发控制时，AI 会引入：① 去掉锁后的竞态条件（高并发下余额负数、状态覆盖）；② 在锁保护范围外读取被锁变量导致脏读；③ 修改锁 key 构造规则导致锁失效但不报错。并发 bug 在本地单线程测试中不会复现。

---

### c) 幂等机制识别

**适用 KB section**：§6 隐性约束

**通用识别信号**：
- 写操作入参包含外部传入的业务流水号（`tradeNo`、`orderId`、`requestId`、`idempotencyKey`）
- 写操作前先查「是否已存在」，命中则直接返回已有结果
- 唯一约束（数据库 / 内存）兜底防重复插入，并有对应的冲突捕获逻辑
- 操作完成后写入幂等记录表或 Redis key

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `UNIQUE INDEX` + catch `DuplicateKeyException`、`insertOrIgnore`、`selectOne(Wrappers.eq("trade_no", x))`、`@Idempotent` 自定义注解 |
| Python | `get_or_create()`（Django）、unique_together、`try/except IntegrityError`、`INSERT ... ON CONFLICT DO NOTHING` |
| TypeScript/JS | `upsert`（Prisma）、`findOrCreate`（Sequelize）、`insertIgnore`（Knex）、Redis `SETNX` |
| Go | `INSERT ... ON CONFLICT DO NOTHING`、`errors.Is(err, ErrAlreadyExists)`、幂等记录表查重 |
| C#/.NET | `AddOrUpdate`（ConcurrentDictionary）、`INSERT ... ON CONFLICT`、EF `AddIfNotExists` 模式 |

**提取方法**：
1. 搜索写操作入参中的「流水号」字段命名规律
2. 确认「先查后写」是否有完整的命中即返回逻辑（而非每次新建）
3. 确认是否依赖数据库唯一索引兜底，以及异常处理是否正确（不能吞掉异常）
4. 写入 KB §6：说明幂等 key 来源、防重机制、命中后的返回语义

**AI 易错点**：不识别幂等时，AI 会：① 去掉「先查后写」的查询步骤导致重复写入；② 修改幂等 key 字段导致同一请求被多次执行；③ 在改写操作后忘记同步更新幂等记录，导致重试返回旧结果。

---

### d) 多租户 / 分表路由

**适用 KB section**：§6 隐性约束 + §7 验证路径

**通用识别信号**：
- 表名或索引名包含数字后缀 / 租户 ID 后缀（`orders_0`、`user_tenant_123`）
- 存在在请求生命周期内设置「当前租户 / 分片键」的上下文切换点
- 存在拦截器 / 插件 / 中间件负责将逻辑表名改写为物理表名
- 多处显式 `tenantId`、`shardKey`、`settingId` 传参，或 ThreadLocal / 上下文中隐式注入
- 存在全局表（不分表）与分表共存，有白名单或排除列表

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `@TableName` + MyBatis 插件改写、`BusinessContextHolder.set()`、`ShardingKey`、`TenantContext`、ShardingSphere / `dynamic-datasource` |
| Python | `using(db=tenant_db)`（Django）、schema 切换、`set_tenant()`、custom DB router |
| TypeScript/JS | Prisma `$extends`、TypeORM `setSchema`、分库中间件、`cls-hooked` 注入 tenantId |
| Go | GORM `Table(tableName)`、context 注入 tenantId、分库分表中间件（gorm-sharding） |
| C#/.NET | EF 动态 schema、`IHttpContextAccessor` 注入 tenantId、ABP Framework 多租户 |

**提取方法**：
1. 找到路由逻辑核心入口（拦截器 / 插件 / 上下文 set 点）
2. 枚举：哪些表是分表、哪些是全局表（禁止分表）
3. 记录：分片键来源（入参 / ThreadLocal / 请求头）、切换时机、重置时机
4. 写入 KB §6：分表域范围 + 禁止加入分表的全局表 + 切换方式
5. 写入 KB §7：查询分表数据时需指定物理后缀的 curl / SQL 示例

**AI 易错点**：不识别分表路由时，AI 会：① 查基表（模板表）误以为无数据；② 不设上下文直接调用 Service 导致路由错误或报错；③ ALTER TABLE 只改了基表，未同步到物理分表；④ 把全局配置表错误加入分表初始化，导致路由乱跳。

---

### e) 事件驱动识别

**适用 KB section**：§5 流程 / MQ 入口索引 + 跨域联动候选

**通用识别信号**：
- 存在消息队列 producer（发布）和 consumer（消费）配对
- 存在异步事件（`ApplicationEventPublisher.publishEvent`、`@EventListener`、`EventEmitter.emit`）
- 存在 Webhook 回调处理（接收外部事件）
- 存在定时任务触发后续业务流程

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `rabbitTemplate.convertAndSend`、`@RabbitListener`、`kafkaTemplate.send`、`@KafkaListener`、`ApplicationEventPublisher`、`@EventListener`、`@TransactionalEventListener` |
| Python | Celery `@app.task`、Django signals `post_save.connect`、`pika` / `confluent_kafka` producer/consumer |
| TypeScript/JS | `EventEmitter`、`Bull` / `BullMQ` queue、`amqplib`、`kafkajs`、NestJS `@EventPattern`、`@MessagePattern` |
| Go | `channel` 异步传递、NATS / Kafka / RabbitMQ client、cron job `github.com/robfig/cron` |
| C#/.NET | `MassTransit`、`NServiceBus`、`IMediator.Publish`（MediatR）、Hangfire `BackgroundJob.Enqueue` |

**提取方法**：
1. 收集 `depth_scanner.py` 的 `event_patterns`
2. 对每个 producer：记录 topic/event type、携带数据结构、触发时机（哪个操作后）
3. 对每个 consumer：记录订阅的 topic/event type、处理逻辑入口、失败策略（重试 / 死信）
4. 识别跨域联动：producer 在 A 域，consumer 在 B 域 → 跨域联动候选
5. 写入 §5：事件矩阵（触发域、topic、消费域、处理入口）；跨域的写入跨域联动候选说明

**AI 易错点**：不识别事件驱动时，AI 会：① 以为删除 A 域实体只影响 A 域，漏掉 B 域的 consumer 级联处理；② 以为操作是同步完成，但实际结果需等消息消费后才落库；③ 把 producer 和 consumer 在不同服务视为无关代码，修改一方接口但不更新另一方。

---

### f) 配置 / DSL 格式提取

**适用 KB section**：§6 隐性约束（格式规范）

**通用识别信号**：
- 某个字段存储 JSON / YAML / 自定义字符串，被业务代码解析后才使用
- 存在专门的 DSL 解析器 / 转换器类（`*Parser`、`*Converter`、`*Resolver`、`*Deserializer`）
- 存在枚举驱动的格式分支（`switch(type)` 决定如何解析同一字段）
- 规则引擎 / 流程引擎的条件和参数以结构化数据存储在数据库中

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `JsonNode`、`ObjectMapper.readValue`、`@JsonTypeInfo`、`@JsonSubTypes`、`JdbcType`、TypeHandler |
| Python | `json.loads(field_value)`、`pydantic.parse_obj`、`jsonschema.validate`、Django `JSONField` |
| TypeScript/JS | `JSON.parse()`、`zod.parse()`、`ajv.validate()`、Prisma `Json` 类型、TypeORM `type: 'jsonb'` |
| Go | `json.Unmarshal`、`encoding/json`、结构体 tag `json:"field,omitempty"`、自定义 `UnmarshalJSON` |
| C#/.NET | `JsonSerializer.Deserialize`、`Newtonsoft.Json`、`System.Text.Json`、EF value converter |

**提取方法**：
1. 找到解析器入口，反向追踪它处理的数据库字段或入参字段
2. 列出所有 `type` 枚举值，对每个值说明格式要求（必填字段、值域、嵌套结构）
3. 若有格式版本（v1/v2），说明版本区分字段和兼容逻辑
4. 提取典型合法样本（JSON / YAML 片段）写入 KB §6
5. 注明：哪些字段 null 合法、哪些 null 会静默报错（最常见坑）

**AI 易错点**：不提取 DSL 格式时，AI 会：① 生成不符合格式的数据导致解析异常（且报错不指向格式问题而是业务逻辑深处）；② 漏填必须但无 `@NotNull` 约束的字段导致运行时 NPE；③ 在新功能中存入旧格式版本，触发版本兼容问题。

---

### g) 软删除模式

**适用 KB section**：§6 隐性约束（查询约束）

**通用识别信号**：
- 实体有 `deleted_at`、`is_deleted`、`biz_status`、`status` 字段用于标记删除而非物理删除
- 查询方法默认过滤已删除记录（框架级 `@Where`、插件级拦截、手动 `.ne("status", DELETED)`）
- 部分查询场景需要查到「已删除」记录（如审计、级联清理、查历史）
- 存在同一外键有多条记录只有一条「活跃」的情况（软删除 + 新建替代旧版本）

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `@TableLogic`（MyBatis-Plus）、`@Where(clause = "deleted = 0")`（Hibernate）、`.ne(BizStatus, DELETED)` |
| Python | `SoftDeleteQuerySet`、`objects.filter(is_deleted=False)`、django-safedelete、`deleted_at__isnull=True` |
| TypeScript/JS | Prisma `where: { deletedAt: null }`、TypeORM `@DeleteDateColumn`、Sequelize `paranoid: true` |
| Go | `db.Where("deleted_at IS NULL")`（GORM `soft_delete`）、手动 `AND is_deleted = 0` |
| C#/.NET | EF `HasQueryFilter(e => !e.IsDeleted)`、`ISoftDelete` 接口、全局过滤器 |

**提取方法**：
1. 找到软删除字段和框架级 / 全局过滤器
2. 搜索「绕过默认过滤」的场景（`Unscoped()`、`withDeleted()`、手动 `includeDeleted`）
3. 梳理：哪些查询场景必须包含已删除记录（级联清理、幂等查重、审计溯源）
4. 写入 KB §6：说明过滤默认行为、绕过方式、各查询场景的过滤口径

**AI 易错点**：不识别软删除时，AI 会：① 在幂等查重时查不到已软删除的同 key 记录，导致重复创建；② 级联清理时忘记处理已软删除的子实体，留下孤儿数据；③ 直接 `DELETE FROM` 物理删除，绕过业务状态流转。

---

### h) 实体字段语义陷阱

**适用 KB section**：§4 表/字段入口 + §6 隐性约束（**AI 易错点** 标签）

**通用识别信号**：
- 实体类中的字段存在"看名字猜用法会写出 bug"的隐式语义
- 同名字段在不同实体/表中指代不同概念
- NULL 值有特殊业务含义（不是"未设置"而是"永久/无限/默认"）
- 字段类型与直觉不符（如 `Integer` 存储的是枚举 code 而非数值、`String` 存储 JSON 而非文本）
- `logic_id` / `version` / `biz_status` 等有隐式框架行为的字段

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `@TableField(fill = FieldFill.INSERT)` 自动填充、`@Version` 乐观锁、`@TableLogic` 逻辑删除、`@TableName` 实体类有多个同名字段（如多处 `tid`）、字段注释与实际行为不一致 |
| Python | `default=None` 但 None 有业务语义、`ForeignKey` 名与实际指向不一致、`verbose_name` 与实际用途偏差 |
| TypeScript/JS | `@Column({ nullable: true })` 但 null 有语义、TypeORM relation 名与实际实体不匹配 |
| Go | 同名 struct tag 在不同 struct 中映射到不同列、`json:"-"` 隐藏的字段在 DB 中有值 |
| C#/.NET | `[NotMapped]` 字段有计算逻辑、`[Column("real_name")]` 字段映射名与属性名不同 |

**提取方法**：
1. 从 `depth_scanner.py` 的 `entity_fields` 输出中找到主实体的所有字段
2. 对每个字段检查：① 名称是否在多个实体中出现但含义不同？② 是否允许 NULL 且 NULL 有业务语义？③ 类型是否有隐式行为（乐观锁/自动填充/逻辑删除）？④ 是否是外键但命名暗示的指向与实际指向不一致？
3. 将确认的陷阱写入 §6 并标 **AI 易错点**；字段完整列表写入 §4
4. 特别关注：多个表共享同名字段但语义不同（如 `tid` 在主表是标识号、在流水表是流水号）——这类在代码补全时极易被 AI 混用

**AI 易错点**：不提取字段语义时，AI 会：① 写 SQL 查询时用 `WHERE expire_time > NOW()` 漏掉 NULL=永久有效的记录；② 在不同 Service 间传递同名字段时混淆含义（如把"客户 TID"传给期望"流水 TID"的接口）；③ 删除或修改有隐式框架行为的字段（如去掉 `@Version` 注解导致并发失控）。

---

### i) JSON 字段格式提取

**适用 KB section**：§6 隐性约束（格式规范）

**通用识别信号**：
- 实体字段类型为 `String`/`Text`/`JSONB` 但实际存储结构化 JSON，有专门的反序列化逻辑
- 存在 TypeHandler / ValueConverter / 自定义序列化器将 DB 字段转为 DTO 对象
- 字段的合法结构由枚举 `type` 字段路由到不同的子格式
- 存在"格式不对时静默失败"的解析逻辑（try-catch 吞异常返回 null/空对象）

**语言变体信号**：

| 语言栈 | 信号举例 |
|--------|----------|
| Java/Kotlin | `JSON.parseObject(field, XxxDTO.class)`、`@TableField(typeHandler = JacksonTypeHandler.class)`、`ObjectMapper.readValue`、`@Convert(converter = ...)`、`JsonNode` 字段 |
| Python | `JSONField()`（Django）、`json.loads(self.config_field)`、Pydantic model 从 `str` 列解析 |
| TypeScript/JS | `JSON.parse(entity.configColumn)` → typed object、Prisma `Json` 类型、`@Column({ type: 'jsonb' })` |
| Go | `json.Unmarshal([]byte(field), &struct{})`、`gorm:"type:jsonb"` tag |
| C#/.NET | `[Column(TypeName = "jsonb")]` + 自定义 ValueConverter、`JsonSerializer.Deserialize<T>(field)` |

**提取方法**：
1. 从 `depth_scanner.py` 的 `json_field_patterns` 获取候选字段列表
2. 对每个命中字段：追踪其反序列化目标类型（DTO/record/struct），列出所有字段含义和值域
3. 确认：① 哪些子字段必填（缺失会 NPE/异常）？② 枚举 `type` 字段的全部合法值？③ NULL 是否合法（整个 JSON 列为 null vs JSON 内某个 key 为 null）？④ 是否有格式版本兼容逻辑？
4. 写入 §6：给出一个"最小合法样本"JSON 片段 + "缺失关键字段时的报错表现"
5. 重点标注：哪些字段"前端漏传导致 Jackson 反序列化为 null，但代码不校验直接用"——这是最常见的运行时 NPE 来源

**AI 易错点**：不提取 JSON 字段格式时，AI 会：① 生成不符合格式的数据（如漏掉必填的 `type` 字段导致解析分支走到 default/null）；② 在 DB 中直接 UPDATE JSON 字段时破坏结构（如把数组格式写成对象格式）；③ 新增功能时在 JSON 中加字段但未同步修改反序列化 DTO，导致字段被静默丢弃。

---

## 语言变体信号汇总表

| 模式 | Java/Kotlin | Python | TypeScript/JS | Go | C#/.NET |
|------|-------------|--------|---------------|-----|---------|
| 状态机 | `enum` + `Assert` 前置 | `choices=` + 校验 | union type + `switch` | `const iota` + 错误返回 | `enum` + `switch` throw |
| 并发控制 | `@Version` / `SELECT FOR UPDATE` / Redis NX | `select_for_update()` / Redis NX | `$transaction` / Redis NX | `sync.Mutex` / `WHERE version=` | `[Timestamp]` / `IsolationLevel` |
| 幂等 | `DuplicateKeyException` + `insertOrIgnore` | `get_or_create()` / `IntegrityError` | `upsert` / `findOrCreate` | `ON CONFLICT DO NOTHING` | `AddOrUpdate` / `ON CONFLICT` |
| 分表路由 | `@TableName` + 拦截器 / `BusinessContextHolder` | DB router / schema 切换 | 中间件 / `Table()` | `Table(name)` / context 注入 | EF 动态 schema / ABP 多租户 |
| 事件驱动 | `@RabbitListener` / `@EventListener` | Celery / Django signal | Bull / `@EventPattern` | channel / NATS client | MassTransit / MediatR |
| DSL 格式 | `ObjectMapper` / TypeHandler | `json.loads` / pydantic | `JSON.parse` / zod | `json.Unmarshal` / 自定义 UnmarshalJSON | `JsonSerializer` / EF value converter |
| 软删除 | `@TableLogic` / `@Where` | `paranoid` / `SoftDeleteQuerySet` | Prisma `deletedAt` / `paranoid: true` | GORM `soft_delete` / `WHERE deleted_at IS NULL` | EF `HasQueryFilter` |
| 字段语义陷阱 | 多处同名 `tid` 含义不同 / `@Version` / `NULL=永久` | `default=None` 有语义 / `ForeignKey` 名不匹配 | `nullable: true` + null 有语义 | 同名 tag 不同含义 / `json:"-"` | `[NotMapped]` + 计算逻辑 / 列映射名不同 |
| JSON 字段 | `JacksonTypeHandler` / `JSON.parseObject` | `JSONField()` / `json.loads` | `JSON.parse` → typed / Prisma `Json` | `json.Unmarshal` / `type:jsonb` | `jsonb` Column + ValueConverter |

---

## 从 depth_scanner.py 输出到 KB 的映射规则

`depth_scanner.py` 的 JSON 输出字段 → 本文对应模式 → KB 落档位置：

| 输出字段 | 对应模式 | KB 落档 section |
|----------|----------|-----------------|
| `status_patterns` | 状态机提取（模式 a） | §2 核心流程 / 状态机 |
| `concurrency_patterns` | 并发控制识别（模式 b） | §6 隐性约束 |
| `idempotent_patterns` | 幂等机制识别（模式 c） | §6 隐性约束 |
| `sharding_patterns` | 多租户 / 分表路由（模式 d） | §6 隐性约束 + §7 验证路径 |
| `event_patterns` | 事件驱动识别（模式 e） | §5 流程索引 + 跨域联动候选 |
| `dsl_patterns` | 配置 / DSL 格式提取（模式 f） | §6 隐性约束 |
| `soft_delete_patterns` | 软删除模式（模式 g） | §6 隐性约束 |
| `entity_fields` | 实体字段语义陷阱（模式 h） | §4 表/字段入口 + §6 隐性约束 |
| `json_field_patterns` | JSON 字段格式提取（模式 i） | §6 隐性约束（格式规范） |
| `framework_components` | — | §3 代码入口 + §5 流程索引（按组件类型归入对应域） |
| `runnable_project_type` | — | 根 `AGENTS.md` 运维速查（见下节） |

**处理规则**：
- `depth_scanner.py` 输出的是原始信号，不是最终 KB 内容。模型必须结合业务语义判断信号的实际含义（例如 `version` 字段可能是乐观锁，也可能是配置版本号）。
- 同一信号可能命中多个模式（例如幂等机制通常也依赖并发控制）；两个模式的 KB 条目应互相引用，不要重复展开。
- `framework_components` 列出的组件按业务域归入对应 KB，不单独生成「技术组件索引」文档。

---

## 运维速查条件生成规则

`runnable_project_type` 的值决定根 `AGENTS.md` 是否以及如何生成运维速查段。只有确认为可运行服务（而非纯库或 CLI 工具）时才生成。

### spring-boot

- **端口**：从 `application*.properties` / `application*.yml` 中的 `server.port` 读取；多模块项目逐模块读取
- **模块与启动别名**：从各子模块 `pom.xml` 中找 `spring-boot-maven-plugin` 的 `<configuration>`，或读 `spring-boot:run` 的 `mainClass`
- **运维速查内容**：
  - 各模块别名 → 端口 → Maven 模块路径
  - `mvn -pl <module> spring-boot:run` 启动命令
  - 日志路径（`logging.file.name` 或约定路径 `logs/{APP_NAME}.log`）
  - 健康检查端点（`/actuator/health`，若已引入 actuator）

### django

- **端口**：从 `settings.py` 读取 `PORT`、`ALLOWED_HOSTS`，或从 `Procfile` / `docker-compose.yml` 读取
- **运维速查内容**：
  - `python manage.py runserver [port]` 启动命令
  - `settings.py` 路径 + `DATABASES` 配置位置
  - 日志配置位置（`LOGGING` dict）

### express / nestjs

- **端口**：从 `.env` 的 `PORT` 变量，或 `app.listen(PORT)` 调用，或 `package.json` `scripts.start` 命令
- **运维速查内容**：
  - `npm run start` / `npm run start:dev` 命令
  - `.env.example` 中需配置的环境变量清单
  - 日志框架（`winston`、`pino` 等）和日志路径

### docker / docker-compose

- **端口**：从 `Dockerfile` 的 `EXPOSE` 指令，或 `docker-compose.yml` 的 `ports` 映射
- **运维速查内容**：
  - `docker-compose up` / `docker build` 启动命令
  - 必填环境变量（`environment` 节 + `.env.example`）
  - 健康检查配置（`healthcheck`）

### library / cli / unknown

跳过运维速查段。在根 `AGENTS.md` 中注明「本项目为库 / CLI 工具，无独立运行服务，不生成运维速查」。

---

## 预算控制

- 每个模式的提取不超过 2 次 grep / 脚本调用；信号足够判断即停止深挖
- 同一模式在多个业务域均有命中时，先写入公共 Guide 候选，再在各 KB §6 引用 Guide，避免重复展开
- `depth_scanner.py` 输出为空的字段不做额外搜索，直接在 KB 对应 section 注「未发现该模式」
