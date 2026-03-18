# Lessons Learned — AI Agent Baseline v0.1

## 1. Structure Before Intelligence

A working system requires:
- schemas
- state
- orchestration
- persistence

LLMs should come AFTER structure, not before.

---

## 2. Schema Enforcement is Critical

Without strict schemas:
- outputs drift
- debugging becomes impossible
- system becomes non-deterministic

Pydantic + enums significantly improved reliability.

---

## 3. Naming Consistency Matters

Small mismatches caused major failures:
- tools vs tools_used
- status vs completion_status

Consistent naming is essential in multi-stage systems.

---

## 4. Python Package Discipline is Non-Negotiable

Missing:
- `__init__.py`
- proper imports

led to repeated failures.

System-level projects require clean package structure.

---

## 5. Separation of Concerns Prevents Chaos

Clear boundaries between:
- schemas
- runtime
- workflows
- tools

made debugging and iteration manageable.

---

## 6. Tool Execution Must Be Controlled

Direct function calls:
- break abstraction
- reduce security

A registry-based approach is necessary for:
- safety
- extensibility
- auditability

---

## 7. Persistence Changes Everything

Before persistence:
- system was theoretical

After persistence:
- system became inspectable
- outputs became verifiable
- debugging improved significantly

---

## 8. Serialization is a Hidden Complexity

Mixing:
- enums
- Pydantic models
- Python objects

requires careful handling.

Custom serialization logic is necessary.

---

## 9. Debugging is Part of System Design

Most time was spent on:
- imports
- structure
- schema alignment

Not on “AI logic”

This is normal for real systems.

---

## 10. This is a Foundation, Not a Product

The system is:
- structured
- working
- extensible

But not yet:
- intelligent
- scalable
- production-ready

---

## Final Insight

You are no longer building "AI scripts".

You are building:

> a structured agent runtime system

This changes how:
- code is written
- problems are approached
- systems are designed
- 
