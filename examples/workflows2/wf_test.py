from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.workflows2.wf import wf
from aiida.orm.data.simple import Int
from aiida.workflows2.fragmented_wf import FragmentedWorkfunction
from aiida.orm.data.simple import NumericType
from aiida.workflows2.run import run

@wf
def sum(a, b):
    return a + b


@wf
def prod(a, b):
    return a * b


@wf
def add_multiply_wf(a, b, c):
    return prod(sum(a, b), c)


class AddMultiplyWf(FragmentedWorkfunction):
    @classmethod
    def _define(cls, spec):
        super(FragmentedWorkfunction, cls)._define(spec)

        spec.input("a", valid_type=NumericType)
        spec.input("b", valid_type=NumericType)
        spec.input("c", valid_type=NumericType)
        spec.outline(
            cls.sum,
            cls.prod
        )

    def sum(self, ctx):
        ctx.sum = self.inputs.a + self.inputs.b

    def prod(self, ctx):
        self.out(ctx.sum * self.inputs.c)



if __name__ == '__main__':
    two = Int(2)
    three = Int(3)
    four = Int(4)

    print "WORKFUNCTION:"

    simpledata = add_multiply_wf(two, three, four)
    print "output pk:", simpledata.pk
    print "output value:", simpledata.value

    print(run(AddMultiplyWf, a=two, b=three, c=four))
