from __future__ import (division, absolute_import,
                        print_function, unicode_literals)

import numpy
import theano
import theano.tensor as tensor
from theano.compile.nanguardmode import NanGuardMode

profile=False

def itemlist(tparams):
    return [v for k, v in tparams.items()]

# name(hyperp, tparams, grads, inputs (list), cost) = f_grad_shared, f_update
def adam(lr, tparams, grads, inp, cost):
    gshared = [theano.shared(p.get_value() * 0.,
                             name='%s_grad' % k)
               for k, p in tparams.items()]
    gsup = [(gs, g) for gs, g in zip(gshared, grads)]

    f_grad_shared = theano.function(inp, cost, 
                                    updates=gsup, profile=profile, 
                                    allow_input_downcast=True)

    lr0 = 0.0002
    b1 = 0.1
    b2 = 0.001
    e = 1e-8

    updates = []

    i = theano.shared(numpy.float32(0.))
    i_t = i + 1.
    fix1 = 1. - b1**(i_t)
    fix2 = 1. - b2**(i_t)
    lr_t = lr0 * (tensor.sqrt(fix2) / fix1)

    for p, g in zip(tparams.values(), gshared):
        m = theano.shared(p.get_value() * 0.)
        v = theano.shared(p.get_value() * 0.)
        m_t = (b1 * g) + ((1. - b1) * m)
        v_t = (b2 * tensor.sqr(g)) + ((1. - b2) * v)
        g_t = m_t / (tensor.sqrt(v_t) + e)
        p_t = p - (lr_t * g_t)
        updates.append((m, m_t))
        updates.append((v, v_t))
        updates.append((p, p_t))
    updates.append((i, i_t))

    f_update = theano.function([lr], [], updates=updates,
                               on_unused_input='ignore', profile=profile,
                               allow_input_downcast=True)

    return f_grad_shared, f_update


def adadelta(lr, tparams, grads, inp, cost):
    zipped_grads = [theano.shared(p.get_value() * numpy.float32(0.),
                                  name='%s_grad' % k)
                    for k, p in tparams.items()]
    running_up2 = [theano.shared(p.get_value() * numpy.float32(0.),
                                 name='%s_rup2' % k)
                   for k, p in tparams.items()]
    running_grads2 = [theano.shared(p.get_value() * numpy.float32(0.),
                                    name='%s_rgrad2' % k)
                      for k, p in tparams.items()]

    zgup = [(zg, g) for zg, g in zip(zipped_grads, grads)]
    rg2up = [(rg2, 0.95 * rg2 + 0.05 * (g ** 2))
             for rg2, g in zip(running_grads2, grads)]

    f_grad_shared = theano.function(inp, cost, updates=zgup+rg2up,
                                    profile=profile,
                                    allow_input_downcast=True)

    updir = [-tensor.sqrt(ru2 + 1e-6) / tensor.sqrt(rg2 + 1e-6) * zg
             for zg, ru2, rg2 in
             zip(zipped_grads, running_up2, running_grads2)]
    ru2up = [(ru2, 0.95 * ru2 + 0.05 * (ud ** 2))
             for ru2, ud in zip(running_up2, updir)]
    param_up = [(p, p + ud) for p, ud in zip(itemlist(tparams), updir)]

    f_update = theano.function([lr], [], updates=ru2up+param_up,
                               on_unused_input='ignore', profile=profile,
                               allow_input_downcast=True)

    return f_grad_shared, f_update


def rmsprop(lr, tparams, grads, inp, cost):
    zipped_grads = [theano.shared(p.get_value() * numpy.float32(0.),
                                  name='%s_grad' % k)
                    for k, p in tparams.items()]
    running_grads = [theano.shared(p.get_value() * numpy.float32(0.),
                                   name='%s_rgrad' % k)
                     for k, p in tparams.items()]
    running_grads2 = [theano.shared(p.get_value() * numpy.float32(0.),
                                    name='%s_rgrad2' % k)
                      for k, p in tparams.items()]

    zgup = [(zg, g) for zg, g in zip(zipped_grads, grads)]
    rgup = [(rg, 0.95 * rg + 0.05 * g) for rg, g in zip(running_grads, grads)]
    rg2up = [(rg2, 0.95 * rg2 + 0.05 * (g ** 2))
             for rg2, g in zip(running_grads2, grads)]

    f_grad_shared = theano.function(inp, cost, updates=zgup+rgup+rg2up,
                                    profile=profile,
                                    allow_input_downcast=True)

    updir = [theano.shared(p.get_value() * numpy.float32(0.),
                           name='%s_updir' % k)
             for k, p in tparams.iteritems()]
    updir_new = [(ud, 0.9 * ud - 1e-4 * zg / tensor.sqrt(rg2 - rg ** 2 + 1e-4))
                 for ud, zg, rg, rg2 in zip(updir, zipped_grads, running_grads,
                                            running_grads2)]
    param_up = [(p, p + udn[1])
                for p, udn in zip(itemlist(tparams), updir_new)]
    f_update = theano.function([lr], [], updates=updir_new+param_up,
                               on_unused_input='ignore', profile=profile,
                               allow_input_downcast=True)

    return f_grad_shared, f_update


def sgd(lr,tparams, grads, x, y, cost):
    gshared = [theano.shared(p.get_value() * 0., name='%s_grad' % p.name, borrow = True)
               for p in tparams]
    names = [p.name for p in tparams]
    gsup = [(gs, g) for gs, g, name in zip(gshared, grads, names)]

    f_grad_shared = theano.function([x, y], cost, updates=gsup,
                                    profile=profile,
                                    allow_input_downcast=True)

    pup = [(p, p - lr * g) for p, g in zip(tparams, gshared)]
    f_update = theano.function([lr], [], updates=pup, profile=profile,
                               allow_input_downcast=True)
    

    return f_grad_shared, f_update

def sgd_(lr, tparams, grads, x, y, cost, x_shared, y_shared, batch_size):
    index = tensor.iscalar(name='batch_idx')
    print("batch_size", batch_size)
    for p, g in zip(tparams, grads):
        print(p, g)

    pup = [(p, p - lr * g) for p, g in zip(tparams, grads)]
    f_grad_shared = theano.function([lr, index], outputs=cost, 
                                    updates = pup,
                                    givens = [ 
                                        (y, tensor.cast(y_shared[index * batch_size: (index + 1) * batch_size], 'int32')),
                                        (x, tensor.cast(x_shared[index * batch_size: (index + 1) * batch_size], 'int32'))
                                    ],
                                    profile=profile, 
                                    allow_input_downcast=True)

    return f_grad_shared


def sgd__(lr, tparams, grads, x, y, xm, ym, cost, x_shared, y_shared, xm_shared, ym_shared, batch_size):
    index = tensor.iscalar(name='batch_idx')
    print("batch_size", batch_size)
    for p, g in zip(tparams, grads):
        print(p, g)

    pup = [(p, p - lr * g) for p, g in zip(tparams, grads)]
    f_grad_shared = theano.function([lr, index], outputs=cost, 
                                    updates = pup,
                                    givens = [ 
                                        (y, tensor.cast(y_shared[index * batch_size: (index + 1) * batch_size], 'int32')),
                                        (x, tensor.cast(x_shared[index * batch_size: (index + 1) * batch_size], 'int32')),
                                        (ym, tensor.cast(ym_shared[index * batch_size: (index + 1) * batch_size], 'int32')),
                                        (xm, tensor.cast(xm_shared[index * batch_size: (index + 1) * batch_size], 'int32'))
                                    ],
                                    profile=profile, 
                                    allow_input_downcast=True, on_unused_input='ignore')

    return f_grad_shared

