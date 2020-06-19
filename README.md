# `nmigen_dg` - the nMigen dogelang DSL

[nMigen](https://m-labs.hk/gateware/nmigen/) is a Hardware Description Language (HDL) hosted in Python.

* It is an *internal* DSL (Domain Specific Language), which means it not only allows you to construct hardware using the DSL, but it also allows you to reap the benefits of the hosted it is hosted in.
* Python is an accessible language with wide availability and a focus on readability.
* Python is however not really suited for hosting these kinds of DSLs, due to having few metaprogramming facilities to create any custom syntax, making both nMigen (and it predecessor Migen) awkward to use.
* Other languages like Scala, V and Rust more better suited to host internal DSLs, with great HDL examples being Chisel3 and SpinalHDL.

[Dogelang](https://pyos.github.io/dg/) (`dg`) is a Haskell-ish frontend for the Python VM, offering us an alternative syntax to use the already existing nMigen.

`nmigen_dg` is a layer on top of nMigen, with an interface more suited for dg. The aim of `nmigen_dg` is to make nMigen as a HDL more **readable**.


# Strengths

* `dg` *looks* more declarative, fitting for implementing logic in hardware
* `dg` provides a way to define inline functions, allowing us more freedom to design a DSL.
* `dg` interfaces with existing python code without issue, making partial use a non-issue.
* `dg` reduces a lot of the visual noise of python (`self.*` becomes `@*`, `with` is wrapped in higher order functions)
* `dg` allows you to create custom tokens for the `dg` parser/compiler



# Ideas

My aim is readability. To achieve this I aim to *minimize syntactic noise* and to achieve a syntax as close to bare `dg` as possible.
The following is written with the assumption that you've read the [guide to dg](https://pyos.github.io/dg/tutorial/).

## Clear separation between hardware and control-flow

I opted to rename the `if/elif/else` constructs in nMigen to `when/otherwise`.
This is to better mentally separate the execution flow from the hardware logic being implemented.
`when` is inspired by [Chisel3](https://www.chisel-lang.org/), and `dg` already has a `otherwise`, which then naturally replaced `else`


## Abuse lambdas and their signatures

In nMigen we construct Records (others call them bundles or structs) from a list of pairs of names and sizes:

	my_record = Record([
		("foo", 8),
		("bar", 4),
		("baz", 4),
	])

If we limit the field names to be valid identifiers, we can make the record form a list of lambdas by inspecting the name of their arguments. In `nmigen_dg` we write:

	my_record = Record
		foo -> 8
		bar -> 4
		baz -> 4

This can also used to create state machines! The following:

	with m.FSM() as fsm:
		with m.State("START"):
			...
			m.next = "DATA"
		with m.State("DATA"):
			...
			m.next = "STOP"
		with m.State("STOP"):
			...

	x = fsm.ongoing("DATA")

, can with a shim in `dg` become:

	fsm = FSM m
		START ->
	    	...
			START |>. DATA
		DATA ->
			...
			DATA |>. STOP
		STOP ->
			...

	x = fsm.ongoing.DATA

*(syntax for states transition are subject to change)*



# Weaknesses

* It is a new syntax to learn, with some unintuitive operator precedence when coming from Python.

* The author of `dg` says not to use the language for anything serious.

* The author of `dg` is at the time of writing the sole contributor, making the language very fragile.

* The transition to Python 3.8 (which changed how the VM stack is is cleaned) is only partway complete at the time of writing.

* `dg` is selfhosted, and cannot be bootstrapped from bare Python.
  If CPython decides to make a radical change to its bytecode format, `dg` might die.

* `dg` constructs different bytecode than than we would expect from python, making the stack frame inspection in nMigen (to determine names) not always work.

A lot of these can be overcome by contributing to `dg`.


# Examples and tests

[These nMigen example](https://github.com/m-labs/nmigen/tree/master/examples/basic) has been translated to `dg` in `examples/`, with line numbers somewhat preserved. First:

	poetry install

,then run and compare the output:

	poetry run ./examples/alu_hier.py generate
	poetry run ./examples/alu_hier.dg generate

Or run and compare all of them:

	poetry run ./test_examples.py | column -s: -t

If you have python 3.8 installed. Install python3.7 alongside and run as follows:

	python3.7 -m easy_setup pip
	python3.7 -m pip install poetry
	python3.7 -m poetry ...
