# `nmigen_dg` - the nMigen dogelang DSL

[nMigen](https://nmigen.info/nmigen/latest/) is a Hardware Description Language (HDL) hosted in Python.

* It is an *internal* DSL (Domain Specific Language), which means it not only allows you to construct hardware using the DSL, but it also allows you to reap the benefits of the language it is hosted in.
* Python is an accessible language with wide availability and a focus on readability.
* Python is however not really suited for hosting these kinds of DSLs, due to having few metaprogramming facilities to create any custom syntax, making both nMigen (and it predecessor Migen) awkward to use.
* Other languages like Scala, V and Rust more better suited to host internal DSLs, with great HDL examples being Chisel3 and SpinalHDL.

[Dogelang](https://pyos.github.io/dg/) (`dg`) is a Haskell-ish frontend for the Python VM, offering us an alternative syntax to use the already existing nMigen.

`nmigen_dg` is a layer on top of nMigen, with an interface more suited for dg. The aim of `nmigen_dg` is to make nMigen as a HDL more **readable**.


# `dg` Strengths:

* `dg` *looks* more declarative, fitting for implementing logic in hardware
* `dg` provides a way to define inline functions, allowing us more freedom to design a DSL.
* `dg` interfaces with existing python code without issue, making partial use a non-issue.
* `dg` reduces a lot of the visual noise of python (`self.*` becomes `@*`, `with` is wrapped in higher order functions)
* `dg` allows you to create custom tokens for the `dg` parser/compiler



# Ideas:

My aim is readability. To achieve this I aim to *minimize syntactic noise* and to achieve a syntax as close to normal `dg` as possible.
The following presents examples written in `dg`. Refer to the [guide to dg](https://pyos.github.io/dg/tutorial/) if needed.

## Get rid of `self.`

This one is basically free.
`dg` expands the prefix `@` into `self.`.
This reduces the size of many statements and makes the code more reminicient of [pyrope](https://masc.soe.ucsc.edu/pyrope.html).
We could then stick to the design convention that `@` means module io, and we now get nice syntax highligting for these for free.


## What the `.eq()`?

Most HDLs lets you drive registers/wires/signals with some kind of operator derived from `=`

* Verilog use `assign target = source;`
* Chisel3 use `target := source`
* Both `=` and `:=` are taken in `dg`

Python does not have any operators to spare for this purpose, and therefore the nMigen team landed on `target.eq(source)`.
Most Python programmers read `eq` as *"equals"*, opening the gates for you to confuse the assignment with an equality check.

`nmigen_dg`, allowing you to create custom operators, therefore introduces an alternative operator: `target ::= source`.


## Infer `m` from context

nMigen has you prod at the `m` variable to create your hardware.
If we turn all the HDL statements into functions instead of methods, and disallow threading during elaboration, we can get rid of `m` everywhere! This:

	elaborate = platform ~>
		m = Module!
		m.d.comb += ($a ::= ($b + $c))
		return m

, can become

	elaborate = platform ~> m where with m = Module! =>

		Comb$ $a ::= ($b + $c)



## A more clear separation between hardware constructs and elaboration program-flow

`If` became awfully close to the existing keyword `if` after i got rid of the `with m.` prefix.
I opted to rename the `If/Elif/Else` constructs in nMigen to `When`.
This change is to better mentally separate the execution flow from the hardware logic being implemented.
The `When` keyword is inspired by [Chisel3](https://www.chisel-lang.org/), and `dg` already has a `otherwise` constant equal to `True`, which then naturally replaced the `else` case.


## Wrap the context managers in higher order functions

All the `with` statements in nMigen produce a lot of visual noise in the code. In `dg` we can generalize

	with m.If(self.signal):
		m.d.cond += self.out

into

	with m.If(value):
		body()

, where `value` and `body` are `self.signal` and `def body(): m.d.cond += self.out` respectively

This is how `nmigen_dg` creates its `When` construct:

	When
		@input > 0 ,->
			m.d.comb += @positive.eq 1
		@input == 0 ,->
			m.d.comb += @positive.eq 1
		@input < 0 ,->
			m.d.comb += @positive.eq 1
		otherwise ,->
			m.d.comb += @error.eq 1

Here we see the `When` function take in a list of pairs of conditions and body lambdas.
In Python type annotation, the `When` would look something like this:

	def When(*pairs: Sequence[Tuple[Signal, Function]]): ...

Due to some weird operator precedence, this does not work for single-line When blocks:

	When condition ,->
		...

gets parsed as

	(( When condition ), ( -> ... ))

(I think that `,` having a higher precedence than both `$` and `<|` could be a bug)
Therefore, `When` supports this alternative calling convention:

	When condition $ ->
		...

I am thinking of creating a custom operator equal to `,->` but with a lower precedence.

The `Switch` construct is made using the same idea as `When`, turning

	with m.Switch(self.s):
		with m.Case("--1"):
			m.d.comb += self.o.eq(self.a)
		with m.Case("-1-"):
			m.d.comb += self.o.eq(self.b)
		with m.Case("1--"):
			m.d.comb += self.o.eq(self.c)
		with m.Case():
			m.d.comb += self.o.eq(0)

into

	Switch @s
		"--1" ,->
			Comb$ @o ::= @a
		"-1-" ,->
			Comb$ @o ::= @b
		"1--" ,->
			Comb$ @o ::= @c
		otherwise ,->
			Comb$ @o ::= 0


## Abuse lambdas and their signatures

In nMigen we construct Records (others call them bundles or structs) from a list of pairs of field names and their respective sizes:

	my_record = Record([
		("foo", 8),
		("bar", 4),
		("baz", 4),
	])

If we translate this directly to `dg` we get:

	my_record = Record list'
		"foo", 8
		"bar", 4
		"baz", 4

, which is already looking pretty nice, but we can do better!
If we limit the field names to be valid `dg` identifiers (pretty safe assumption), we can make the record out of a list of lambdas. We get their names by inspecting the name of their first parameter, and get the value by calling the lambdas with a dummy value. In `nmigen_dg` we therefore write:

	my_record = Record
		foo -> 8
		bar -> 4
		baz -> 4

This can be further expanded to create state machines! The following nMigen FSM:

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

, can in `nmigen_dg` be written as:

	fsm = FSM
		START ->
	    	...
			START |>. DATA
		DATA ->
			...
			DATA |>. STOP
		STOP ->
			...
	x = fsm.ongoing "DATA"

*(`current_state |>. next_state` subject to change)*



# `dg` Weaknesses:

* It is a new syntax to learn, with some unintuitive operator precedence when coming from Python.

* Syntax for list slicing is missing

* Syntax for type annotations are missing

* Syntax for assertions are missing (can be fixed with a helper function)

* The author of `dg` says not to use the language for anything serious.

* The author of `dg` is at the time of writing the sole contributor, making the language very fragile.

* The transition to Python 3.8 (which changed how the VM stack is cleaned) is only partway complete at the time of writing.

* `dg` is selfhosted, and cannot be bootstrapped from bare Python alone.
  If CPython decides to make a radical change to its bytecode format, `dg` might die.

* `dg` constructs different bytecode than than we would expect from python, making the stack frame inspection in nMigen (to determine names) not always work.

A lot of these issues can be overcome by contributing to `dg`.


# Examples and tests:

[These nMigen examples](https://github.com/m-labs/nmigen/tree/master/examples/basic) has been translated to `nmigen_dg` in `examples/`, with line numbers somewhat preserved.
First:

	poetry install

, then run and compare the output:

	poetry run ./examples/alu_hier.py generate
	poetry run ./examples/alu_hier.dg generate

, or run and compare all of them:

	poetry run ./test_examples.py

If you have python 3.8 installed. Install python3.7 alongside and run it as follows:

	python3.7 -m easy_install pip
	python3.7 -m pip install poetry
	python3.7 -m poetry ...
