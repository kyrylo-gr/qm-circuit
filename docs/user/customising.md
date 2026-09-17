# Customising diagrams

Every appearance value (sizes, colours, fonts, spacing) is a field of [`Style`][qm_circuit.Style]. Pass
`style=` as a dict with only the fields you want to change, and colours are merged into the defaults. All sizes
scale with `size`, the base font size. Wide programs can be wrapped into rows with `max_width`.

The examples below draw this program:

```python
--8<-- "examples/customising.py:program"
```

## Default

```python
--8<-- "examples/customising.py:default"
```

![Default style](diagrams/customising_default.svg){ .qc-figure }

## Larger font

`size` is the base font size in points; every length in the diagram is a multiple of it.

```python
--8<-- "examples/customising.py:larger_font"
```

![Larger font](diagrams/customising_larger_font.svg){ .qc-figure }

## Custom colours

Colour names are the keys of `Style.colors`, such as `pulse`, `measure`, `wait`, `block_fill` and `line`.

```python
--8<-- "examples/customising.py:custom_colours"
```

![Custom colours](diagrams/customising_custom_colours.svg){ .qc-figure }

## Wrapped into rows

`max_width` is in inches. Top-level statements move to a new row once a row would be wider, and a single statement
wider than `max_width` keeps a row to itself.

```python
--8<-- "examples/customising.py:wrapped"
```

![Wrapped into rows](diagrams/customising_wrapped.svg){ .qc-figure }

## All style settings

::: qm_circuit.Style
    options:
      members_order: source
      show_source: false
