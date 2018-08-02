#!/usr/bin/env tarantool

local os   = require('os')
local fio  = require('fio')
local fun  = require('fun')
local log  = require('log')
local json = require('json')
local yaml = require('yaml')

log.info(fio.cwd())
log.info("admin: %s, primary: %s", os.getenv('ADMIN_PORT'), os.getenv('PRIMARY_PORT'))

local compat = {
    log          = 'log',
    memtx_memory = 'memtx_memory',
    unsigned     = 'unsigned',
    string       = 'string',
}

local version = fun.iter(_TARANTOOL:split('-')[1]:split('.')):map(tonumber):totable()

if (version[1] == 1 and version[2] < 8) then
    compat.log          = 'logger'
    compat.memtx_memory = 'slab_alloc_arena'
    compat.unsigned     = 'NUM'
    compat.string       = 'STR'
end

box.cfg{
    listen                = os.getenv('PRIMARY_PORT'),
    log_level             = 5,
    [compat.log]          = 'tarantool.log',
    [compat.memtx_memory] = 400 * 1024 * 1024
}

box.once('initialization', function()
    box.schema.user.create('test', { password = 'test' })
    box.schema.user.create('test_empty', { password = '' })
    box.schema.user.create('test_big', {
        password = '123456789012345678901234567890123456789012345678901234567890'
    })
    box.schema.user.grant('test', 'read,write,execute', 'universe')

    local space = box.schema.space.create('test', {
        format = {
            { type = compat.unsigned, name = 'field1', add_field = 1 },
            { type = compat.unsigned, name = 's1'                    },
            { type = compat.string,   name = 's2'                    },
        }
    })
    space:create_index('primary', {
        type   = 'TREE',
        unique = true,
        parts  = {1, compat.unsigned}
    })
    space:create_index('secondary', {
        type   = 'TREE',
        unique = false,
        parts  = {2, compat.unsigned, 3, compat.string}
    })

    local space = box.schema.space.create('msgpack')
    space:create_index('primary', {
        parts = {1, compat.unsigned}
    })
    space:insert{1, 'float as key', {
        [2.7] = {1, 2, 3}
    }}
    space:insert{2, 'array as key', {
        [{2, 7}] = {1, 2, 3}
    }}
    space:insert{3, 'array with float key as key', {
        [{
            [2.7] = 3,
            [7]   = 7
        }] = {1, 2, 3}
    }}
    space:insert{6, 'array with string key as key', {
        ['megusta'] = {1, 2, 3}
    }}

    local test_hash = box.schema.space.create('test_hash')
    test_hash:create_index('primary', {
        type = 'HASH',
        unique = true
    })
    test_hash:insert{1, 'hash-loc'}
    test_hash:insert{2, 'hash-col'}
    test_hash:insert{3, 'hash-olc'}

    local space = box.schema.space.create('pstring')
    space:create_index('primary', {
        parts = {1, compat.string}
    })
    local yml = io.open(fio.pathjoin(fio.cwd(), "../test/shared/queue.yml")):read("*a")
    local tuple = yaml.decode(yml)[1]
    tuple[1] = "12345"
    box.space._schema:insert(tuple)
end)

function test_1()
    return true, {
        c  = {
            ['106'] = {1, 1428578535},
            ['2']   = {1, 1428578535}
        },
        pc = {
            ['106'] = {1, 1428578535, 9243},
            ['2']   = {1, 1428578535, 9243}
        },
        s  = {1, 1428578535},
        u  = 1428578535,
        v  = {}
    }, true
end

function test_2()
    return {
        k2 = 'v',
        k1 = 'v2'
    }
end

function test_3(x, y)
    return x + y
end

function test_4(...)
    local args = {...}
    log.info('%s', json.encode(args))
    return 2
end

function test_5(count)
    log.info('duplicating %d arrays', count)
    local rv = fun.duplicate{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:take(count):totable()
    log.info('%s', json.encode(rv))
    return rv
end

function test_6(...)
    return ...
end

require('console').listen(os.getenv('ADMIN_PORT'))

