# Source development guidelines

This directory contains the application package. Keep the distinction between
implementation inheritance and structural typing explicit when adding or
refactoring framework types.

## Choosing between an ABC, a protocol, and a base class

Use an **abstract base class (ABC)** when:

- the base supplies shared implementation or state;
- constructing a subclass without a particular override would be invalid;
- nominal membership is semantically important;
- production code intentionally uses `isinstance` with the base; or
- the hierarchy is controlled by this project.

Every class declared as abstract must have at least one meaningful
`@abstractmethod` or abstract property. Do not inherit from `ABC` or specify
`ABCMeta` merely to document that a class is normally subclassed. Add a
regression assertion with `inspect.isabstract` when abstractness is part of the
class contract.

Use a **`typing.Protocol`** when:

- a consumer needs only a small behavioral surface;
- implementations do not need to share code or state;
- third-party implementations or lightweight test doubles should work without
  inheriting a project-specific class; and
- conformance is primarily enforced by the static type checker.

Protocols should be small and consumer-oriented. Concrete implementation
classes do not need to inherit from a protocol because protocol conformance is
structural. Use `@runtime_checkable` only when the application actually needs
an `isinstance` check, remembering that the runtime check verifies attribute
presence rather than complete signatures or semantics.

Use a **plain base class** when it provides shared implementation but has no
genuinely mandatory subclass operation. A class that is intended for reuse but
remains valid to instantiate is not abstract.

## Current framework conventions

- `Sensor` and its behavioral specializations remain nominal ABCs. They contain
  shared state and implementation, and their abstract methods represent real
  requirements for concrete sensors.
- `HaPublisherMixin` remains an ABC because it supplies Home Assistant
  publishing behavior that depends on an explicit host-class contract.
- `Device` and `ModbusDevice` are concrete base classes. Only make them abstract
  if a meaningful common operation must be implemented by every subclass.
- Intermediate sensor implementations such as `RemoteEMSLimit` and
  `ESSPreHeatingTOUTime` are plain base classes when all variation can be passed
  through constructor arguments.
- `Writer` is the preferred protocol example: consumers require a small writer
  interface while implementations remain independent.

## Adding a new abstraction

1. Start from the needs of the consumer rather than mirroring every member of
   an implementation class.
2. Prefer the smallest useful public contract.
3. Use an ABC only when it supplies implementation or needs nominal runtime
   identity and has a real abstract requirement.
4. Use a protocol for structural dependency boundaries, without adding it to a
   concrete class's bases.
5. Use a plain base class when shared code is the only requirement.
6. Add tests for required runtime classification and run Pyright to validate
   structural contracts.

Avoid large protocols that reproduce an implementation hierarchy under a new
name. If a function only needs sensor lookup, for example, define a narrow
`SensorContainer` protocol rather than accepting or describing the full
`Device` API.
