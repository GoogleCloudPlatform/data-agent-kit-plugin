!function($$NODEJS_EXPORTS_OBJECT$$) {
  const __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb)((mod = {exports: {}}).exports, mod), mod.exports;
  };
  /*

   Copyright The Closure Library Authors.
   SPDX-License-Identifier: Apache-2.0
  */
  'use strict';
  var $jscomp = $jscomp || {};
  $jscomp.scope = {};
  $jscomp.ASSUME_ES2020 = !1;
  $jscomp.ASSUME_ES6 = $jscomp.ASSUME_ES2020;
  $jscomp.ASSUME_ES5 = $jscomp.ASSUME_ES6;
  $jscomp.ASSUME_NO_NATIVE_MAP = !1;
  $jscomp.ASSUME_NO_NATIVE_SET = !1;
  $jscomp.ISOLATE_POLYFILLS = !1;
  $jscomp.FORCE_POLYFILL_PROMISE = !1;
  $jscomp.FORCE_POLYFILL_PROMISE_WHEN_NO_UNHANDLED_REJECTION = !1;
  $jscomp.INSTRUMENT_ASYNC_CONTEXT = !0;
  $jscomp.defineProperty =
      $jscomp.ASSUME_ES5 || typeof Object.defineProperties == 'function' ?
      Object.defineProperty :
      function(a, b, c) {
        if (a == Array.prototype || a == Object.prototype) return a;
        a[b] = c.value;
        return a
      };
  $jscomp.getGlobal = function(a) {
    a = [
      'object' == typeof globalThis && globalThis, a,
      'object' == typeof window && window, 'object' == typeof self && self,
      'object' == typeof global && global
    ];
    for (var b = 0; b < a.length; ++b) {
      var c = a[b];
      if (c && c.Math == Math) return c
    }
    throw Error('Cannot find global object');
  };
  $jscomp.global = $jscomp.ASSUME_ES2020 ? globalThis : $jscomp.getGlobal(this);
  $jscomp.IS_SYMBOL_NATIVE =
      typeof Symbol === 'function' && typeof Symbol('x') === 'symbol';
  $jscomp.TRUST_ES6_POLYFILLS =
      !$jscomp.ISOLATE_POLYFILLS || $jscomp.IS_SYMBOL_NATIVE;
  $jscomp.polyfills = {};
  $jscomp.propertyToPolyfillSymbol = {};
  $jscomp.POLYFILL_PREFIX = '$jscp$';
  var JSCompiler_inline_result$jscomp$0,
      classes$jscomp$inline_5 =
          'Int8 Uint8 Uint8Clamped Int16 Uint16 Int32 Uint32 Float32 Float64'
              .split(' ');
  $jscomp.global.BigInt64Array &&
      (classes$jscomp$inline_5.push('BigInt64'),
       classes$jscomp$inline_5.push('BigUint64'));
  JSCompiler_inline_result$jscomp$0 = classes$jscomp$inline_5;
  $jscomp.TYPED_ARRAY_CLASSES = JSCompiler_inline_result$jscomp$0;
  $jscomp.polyfillTypedArrayMethod = function(a, b, c, d) {
    if (b)
      for (var e = 0; e < $jscomp.TYPED_ARRAY_CLASSES.length; e++) {
        var f = $jscomp.TYPED_ARRAY_CLASSES[e] + 'Array.prototype.' + a;
        $jscomp.ISOLATE_POLYFILLS ? $jscomp.polyfillIsolated(f, b, c, d) :
                                    $jscomp.polyfillUnisolated(f, b, c, d)
      }
  };
  $jscomp.polyfill = function(a, b, c, d) {
    b &&
        ($jscomp.ISOLATE_POLYFILLS ? $jscomp.polyfillIsolated(a, b, c, d) :
                                     $jscomp.polyfillUnisolated(a, b, c, d))
  };
  $jscomp.polyfillUnisolated = function(a, b) {
    var c = $jscomp.global;
    a = a.split('.');
    for (var d = 0; d < a.length - 1; d++) {
      var e = a[d];
      if (!(e in c)) return;
      c = c[e]
    }
    a = a[a.length - 1];
    d = c[a];
    b = b(d);
    b != d && b != null &&
        $jscomp.defineProperty(c, a, {configurable: !0, writable: !0, value: b})
  };
  $jscomp.polyfillIsolated = function(a, b, c) {
    var d = a.split('.'), e = d.length === 1;
    a = d[0];
    a = !e && a in $jscomp.polyfills ? $jscomp.polyfills : $jscomp.global;
    for (var f = 0; f < d.length - 1; f++) {
      var g = d[f];
      if (!(g in a)) return;
      a = a[g]
    }
    d = d[d.length - 1];
    c = $jscomp.IS_SYMBOL_NATIVE && c === 'es6' ? a[d] : null;
    b = b(c);
    b != null &&
        (e ? $jscomp.defineProperty(
                 $jscomp.polyfills, d,
                 {configurable: !0, writable: !0, value: b}) :
             b !== c &&
                 ($jscomp.propertyToPolyfillSymbol[d] === void 0 &&
                      (e = Math.random() * 1E9 >>> 0,
                       $jscomp.propertyToPolyfillSymbol[d] =
                           $jscomp.IS_SYMBOL_NATIVE ?
                           $jscomp.global.Symbol(d) :
                           $jscomp.POLYFILL_PREFIX + e + '$' + d),
                  e = $jscomp.propertyToPolyfillSymbol[d],
                  $jscomp.defineProperty(
                      a, e, {configurable: !0, writable: !0, value: b})))
  };
  $jscomp.asyncContextEnter = function() {
    return $jscomp.asyncContextIdentity
  };
  $jscomp.asyncContextStart = function() {
    return $jscomp.asyncContextEnter
  };
  $jscomp.asyncContextIdentity = function(a) {
    return a
  };
  $jscomp.asyncContextWrap = function(a) {
    var b = $jscomp.asyncContextState;
    if (!b[0]) return a;
    var c = b[0], d = function() {
      var e = b[0];
      b[0] = c;
      try {
        return a.apply(this, arguments)
      } finally {
        b[0] = e
      }
    };
    return d
  };
  $jscomp.polyfill('globalThis', function(a) {
    return a || $jscomp.global
  }, 'es_2020', 'es3');
  $jscomp.arrayIteratorImpl = function(a) {
    var b = 0;
    return function() {
      return b < a.length ? {done: !1, value: a[b++]} : {done: !0}
    }
  };
  $jscomp.arrayIterator = function(a) {
    return {
      next: $jscomp.arrayIteratorImpl(a)
    }
  };
  $jscomp.getIteratorPrototype = function() {
    return typeof Iterator != 'undefined' && Iterator.prototype &&
            !Iterator.prototype.next ?
        Iterator.prototype :
        null
  };
  $jscomp.objectCreate =
      $jscomp.ASSUME_ES5 || typeof Object.create == 'function' ?
      Object.create :
      function(a) {
        var b = function() {};
        b.prototype = a;
        return new b
      };
  $jscomp.initSymbol = function() {};
  $jscomp.iteratorPrototype = function(a) {
    var b = $jscomp.getIteratorPrototype() || Object.prototype,
        c = $jscomp.objectCreate(b);
    c.next = a;
    b[Symbol.iterator] || (c[Symbol.iterator] = function() {
      return this
    });
    return c
  };
  $jscomp.underscoreProtoCanBeSet = function() {
    var a = {a: !0}, b = {};
    try {
      return b.__proto__ = a, b.a
    } catch (c) {
    }
    return !1
  };
  $jscomp.setPrototypeOf = $jscomp.ASSUME_ES6 ||
          $jscomp.TRUST_ES6_POLYFILLS &&
              typeof Object.setPrototypeOf == 'function' ?
      Object.setPrototypeOf :
      $jscomp.underscoreProtoCanBeSet() ?
      function(a, b) {
        a.__proto__ = b;
        if (a.__proto__ !== b) throw new TypeError(a + ' is not extensible');
        return a
      } :
      null;
  $jscomp.inherits = function(a, b) {
    a.prototype = $jscomp.objectCreate(b.prototype);
    a.prototype.constructor = a;
    if ($jscomp.ASSUME_ES6 || $jscomp.setPrototypeOf) {
      var c = $jscomp.setPrototypeOf;
      c(a, b)
    } else
      for (c in b)
        if (c != 'prototype')
          if (Object.defineProperties) {
            var d = Object.getOwnPropertyDescriptor(b, c);
            d && Object.defineProperty(a, c, d)
          } else
            a[c] = b[c];
    a.superClass_ = b.prototype
  };
  $jscomp.getConstructImplementation = function() {
    function a() {
      function e() {}
      function f() {}
      new e;
      Reflect.construct(e, [], f);
      return new e instanceof e
    }
    function b(e, f, g) {
      g === void 0 && (g = e);
      g = g.prototype || Object.prototype;
      g = $jscomp.objectCreate(g);
      var h = Function.prototype.apply;
      return (e = h.call(e, g, f)) || g
    }
    if ($jscomp.TRUST_ES6_POLYFILLS && typeof Reflect != 'undefined' &&
        Reflect.construct) {
      if (a()) return Reflect.construct;
      var c = Reflect.construct, d = function(e, f, g) {
        e = c(e, f);
        g && Reflect.setPrototypeOf(e, g.prototype);
        return e
      };
      return d
    }
    return b
  };
  $jscomp.construct = {valueOf: $jscomp.getConstructImplementation}.valueOf();
  $jscomp.polyfill('Iterator', function(a) {
    var b = Object.getPrototypeOf,
        c = typeof Symbol != 'undefined' && Symbol.iterator &&
            [][Symbol.iterator] ?
        [][Symbol.iterator]() :
        null;
    b = (c = c && b ? b(c) : null) && b ? b(c) : null;
    b === Object.prototype && (b = null);
    if (a && b && a.prototype === b) return a;
    var d = function() {
      if (!(this instanceof d) || this.constructor === d)
        throw new TypeError('Abstract Iterator not directly constructable');
    };
    b && (d.prototype = b);
    $jscomp.defineProperty(
        d.prototype, 'constructor', {configurable: !0, writable: !0, value: d});
    d.prototype[Symbol.iterator] || (d.prototype[Symbol.iterator] = function() {
      return this
    });
    return d
  }, 'es_next', 'es3');
  $jscomp.checkIsObject = function(a) {
    if (Object(a) !== a) throw new TypeError('Expected an object');
    return a
  };
  $jscomp.iteratorCloseAbrupt = function(a) {
    try {
      var b = a['return'];
      typeof b == 'function' && b.call(a)
    } catch (c) {
    }
  };
  $jscomp.iteratorCloseNormal = function(a) {
    var b = a['return'];
    if (b != null) {
      if (typeof b != 'function')
        throw new TypeError('Iterator return is not a function');
      $jscomp.checkIsObject(b.call(a))
    }
  };
  $jscomp.iteratorResult = function(a, b) {
    b == null && (b = !0);
    return {
      value: a, done: b
    }
  };
  $jscomp.ITERATOR_STATE_SUSPENDED_START = 1;
  $jscomp.ITERATOR_STATE_SUSPENDED_YIELD = 2;
  $jscomp.ITERATOR_STATE_EXECUTING = 3;
  $jscomp.ITERATOR_STATE_COMPLETED = 4;
  $jscomp.getLazyIteratorState = function(a) {
    if (!a || a.self_ !== a)
      throw new TypeError('Method called on incompatible object');
    a = a.state_;
    if (a === $jscomp.ITERATOR_STATE_EXECUTING)
      throw new TypeError('Generator is already running');
    return a
  };
  $jscomp.lazyIteratorPrototype = null;
  $jscomp.createLazyIterator = function(a, b) {
    var c = $jscomp.lazyIteratorPrototype;
    if (!c) {
      var d = function(e, f) {
        var g = $jscomp.getLazyIteratorState(e);
        if (g != $jscomp.ITERATOR_STATE_COMPLETED) {
          e.state_ = f && g == $jscomp.ITERATOR_STATE_SUSPENDED_START ?
              $jscomp.ITERATOR_STATE_COMPLETED :
              $jscomp.ITERATOR_STATE_EXECUTING;
          try {
            if (f)
              $jscomp.iteratorCloseNormal(e.iter_);
            else {
              var h = e.step_();
              if (h) return e.state_ = $jscomp.ITERATOR_STATE_SUSPENDED_YIELD, h
            }
          } finally {
            e.state_ != $jscomp.ITERATOR_STATE_SUSPENDED_YIELD &&
                (e.state_ = $jscomp.ITERATOR_STATE_COMPLETED,
                 e.step_ = e.iter_ = null)
          }
        }
        return $jscomp.iteratorResult()
      };
      c = $jscomp.lazyIteratorPrototype =
          $jscomp.objectCreate(Iterator.prototype);
      c.next = function() {
        return d(this, !1)
      };
      c.return = function() {
        return d(this, !0)
      };
      c[Symbol.toStringTag] = 'Iterator Helper'
    }
    c = $jscomp.objectCreate(c);
    c.self_ = c;
    c.state_ = $jscomp.ITERATOR_STATE_SUSPENDED_START;
    c.iter_ = a;
    c.step_ = b;
    return c
  };
  $jscomp.validateIteratorCallback = function(a, b) {
    $jscomp.checkIsObject(a);
    if (typeof b != 'function')
      throw $jscomp.iteratorCloseAbrupt(a),
          new TypeError('callback must be a function');
  };
  $jscomp.iteratorMapOrFilter = function(a, b, c) {
    $jscomp.validateIteratorCallback(a, b);
    var d = a.next, e = 0;
    return $jscomp.createLazyIterator(a, function() {
      for (;;) {
        var f = $jscomp.checkIsObject(d.call(a));
        if (f.done) break;
        f = f.value;
        try {
          var g = b(f, e++)
        } catch (h) {
          throw $jscomp.iteratorCloseAbrupt(a), h;
        }
        if (!c || g) return $jscomp.iteratorResult(c ? f : g, !1)
      }
    })
  };
  $jscomp.polyfill('Iterator.prototype.map', function(a) {
    return a || function(b) {
      return $jscomp.iteratorMapOrFilter(this, b, !1)
    }
  }, 'es_next', 'es3');
  $jscomp.iteratorClose = function(a, b) {
    var c;
    b && !b.done && (c = a['return']) && c.call(a)
  };
  $jscomp.iteratorDo = function(a, b, c) {
    $jscomp.validateIteratorCallback(a, b);
    b = a.next;
    for (var d = 0, e; !(e = $jscomp.checkIsObject(b.call(a))).done;) {
      try {
        var f = c(e.value, d++)
      } catch (g) {
        try {
          $jscomp.iteratorClose(a, e)
        } catch (h) {
        }
        throw g;
      }
      if (f) {
        c = a['return'];
        c != null && $jscomp.checkIsObject(c.call(a));
        break
      }
    }
  };
  $jscomp.polyfill('Iterator.prototype.find', function(a) {
    return a || function(b) {
      var c;
      $jscomp.iteratorDo(this, b, function(d, e) {
        if (b(d, e)) return c = d, !0
      });
      return c
    }
  }, 'es_next', 'es3');
  var goog = goog || {};
  goog.global = this || self;
  goog.exportPath_ = function(a, b, c, d) {
    a = a.split('.');
    d = d || goog.global;
    for (var e; a.length && (e = a.shift());)
      if (a.length || b === void 0)
        d = d[e] && d[e] !== Object.prototype[e] ? d[e] : d[e] = {};
      else if (!c && goog.isObject(b) && goog.isObject(d[e]))
        for (var f in b) b.hasOwnProperty(f) && (d[e][f] = b[f]);
      else
        d[e] = b
  };
  goog.CLOSURE_DEFINES = typeof CLOSURE_DEFINES !== 'undefined' ?
      CLOSURE_DEFINES :
      goog.global.CLOSURE_DEFINES;
  goog.CLOSURE_UNCOMPILED_DEFINES =
      typeof CLOSURE_UNCOMPILED_DEFINES !== 'undefined' ?
      CLOSURE_UNCOMPILED_DEFINES :
      goog.global.CLOSURE_UNCOMPILED_DEFINES;
  goog.define = function(a, b) {
    return a = b
  };
  goog.FEATURESET_YEAR = 2012;
  goog.DEBUG = !0;
  goog.LOCALE = 'en';
  goog.TRUSTED_SITE = !0;
  goog.DISALLOW_TEST_ONLY_CODE = !goog.DEBUG;
  goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING = !1;
  goog.readFlagInternalDoNotUseOrElse = function(a, b) {
    var c = goog.getObjectByName(goog.FLAGS_OBJECT_);
    a = c && c[a];
    return a != null ? a : b
  };
  goog.FLAGS_OBJECT_ = 'CLOSURE_FLAGS';
  goog.FLAGS_STAGING_DEFAULT = !0;
  goog.CLOSURE_TOGGLE_ORDINALS = typeof CLOSURE_TOGGLE_ORDINALS === 'object' ?
      CLOSURE_TOGGLE_ORDINALS :
      goog.global.CLOSURE_TOGGLE_ORDINALS;
  goog.readToggleInternalDoNotCallDirectly = function(a) {
    var b = goog.CLOSURE_TOGGLE_ORDINALS;
    a = b && b[a];
    return typeof a !== 'number' ?
        !!a :
        !!(goog.TOGGLES_[Math.floor(a / 30)] & 1 << a % 30)
  };
  goog.TOGGLE_VAR_ = '_F_toggles';
  goog.TOGGLES_ = goog.global[goog.TOGGLE_VAR_] || [];
  goog.GENDERED_MESSAGES_ENABLED = !0;
  goog.GrammaticalGender_ = {OTHER: 0, MASCULINE: 1, FEMININE: 2, NEUTER: 3};
  goog.GRAMMATICAL_GENDER_MAP_ = {
    FEMININE: goog.GrammaticalGender_.FEMININE,
    MASCULINE: goog.GrammaticalGender_.MASCULINE,
    NEUTER: goog.GrammaticalGender_.NEUTER
  };
  goog.viewerGrammaticalGender_ =
      goog.GRAMMATICAL_GENDER_MAP_[goog.GENDERED_MESSAGES_ENABLED && goog.global._F_VIEWER_GRAMMATICAL_GENDER] ||
      goog.GrammaticalGender_.OTHER;
  goog.msgKind = {};
  goog.msgKind.MASCULINE =
      goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.MASCULINE;
  goog.msgKind.FEMININE =
      goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.FEMININE;
  goog.msgKind.NEUTER =
      goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.NEUTER;
  goog.LEGACY_NAMESPACE_OBJECT_ = goog.global;
  goog.provide = function(a) {
    if (goog.isInModuleLoader_())
      throw Error('goog.provide cannot be used within a module.');
    goog.constructNamespace_(a)
  };
  goog.constructNamespace_ = function(a, b, c) {
    goog.exportPath_(a, b, c, goog.LEGACY_NAMESPACE_OBJECT_)
  };
  goog.NONCE_PATTERN_ = /^[\w+/_-]+[=]{0,2}$/;
  goog.getScriptNonce_ = function(a) {
    a = (a || goog.global).document;
    return (a = a.querySelector && a.querySelector('script[nonce]')) &&
            (a = a.nonce || a.getAttribute('nonce')) &&
            goog.NONCE_PATTERN_.test(a) ?
        a :
        ''
  };
  goog.VALID_MODULE_RE_ = /^[a-zA-Z_$][a-zA-Z0-9._$]*$/;
  goog.module = function() {};
  goog.module.get = function() {
    return null
  };
  goog.module.getInternal_ = function() {
    return null
  };
  goog.requireDynamic = function() {
    return null
  };
  goog.importHandler_ = null;
  goog.uncompiledChunkIdHandler_ = null;
  goog.setImportHandlerInternalDoNotCallOrElse = function(a) {
    goog.importHandler_ = a
  };
  goog.setUncompiledChunkIdHandlerInternalDoNotCallOrElse = function(a) {
    goog.uncompiledChunkIdHandler_ = a
  };
  goog.maybeRequireFrameworkInternalOnlyDoNotCallOrElse = function() {};
  goog.ModuleType = {ES6: 'es6', GOOG: 'goog'};
  goog.moduleLoaderState_ = null;
  goog.isInModuleLoader_ = function() {
    return goog.isInGoogModuleLoader_() || goog.isInEs6ModuleLoader_()
  };
  goog.isInGoogModuleLoader_ = function() {
    return !!goog.moduleLoaderState_ &&
        goog.moduleLoaderState_.type == goog.ModuleType.GOOG
  };
  goog.isInEs6ModuleLoader_ = function() {
    var a = !!goog.moduleLoaderState_ &&
        goog.moduleLoaderState_.type == goog.ModuleType.ES6;
    return a ? !0 :
        (a = goog.LEGACY_NAMESPACE_OBJECT_.$jscomp) ?
               typeof a.getCurrentModulePath != 'function' ?
               !1 :
               !!a.getCurrentModulePath() :
               !1
  };
  goog.module.declareLegacyNamespace = function() {
    goog.moduleLoaderState_.declareLegacyNamespace = !0
  };
  goog.module.preventModuleExportSealing = function() {
    goog.moduleLoaderState_.preventModuleExportSealing = !0
  };
  goog.declareModuleId = function(a) {
    if (goog.moduleLoaderState_)
      goog.moduleLoaderState_.moduleName = a;
    else {
      var b = goog.LEGACY_NAMESPACE_OBJECT_.$jscomp;
      if (!b || typeof b.getCurrentModulePath != 'function')
        throw Error(
            'Module with namespace "' + a + '" has been loaded incorrectly.');
      b = b.require(b.getCurrentModulePath());
      goog.loadedModules_[a] = {
        exports: b,
        type: goog.ModuleType.ES6,
        moduleId: a
      }
    }
  };
  goog.setTestOnly = function(a) {
    if (goog.DISALLOW_TEST_ONLY_CODE)
      throw a = a || '',
            Error(
                'Importing test-only code into non-debug environment' +
                (a ? ': ' + a : '.'));
  };
  goog.forwardDeclare = function() {};
  goog.getObjectByName = function(a, b) {
    a = a.split('.');
    b = b || goog.global;
    for (var c = 0; c < a.length; c++)
      if (b = b[a[c]], b == null) return null;
    return b
  };
  goog.addDependency = function() {};
  goog.ENABLE_DEBUG_LOADER = !1;
  goog.logToConsole_ = function(a) {
    goog.global.console && goog.global.console.error(a)
  };
  goog.require = function() {};
  goog.requireType = function() {
    return {}
  };
  goog.basePath = '';
  goog.abstractMethod = function() {
    throw Error('unimplemented abstract method');
  };
  goog.addSingletonGetter = function(a) {
    a.instance_ = void 0;
    a.getInstance = function() {
      if (a.instance_) return a.instance_;
      goog.DEBUG &&
          (goog.instantiatedSingletons_[goog.instantiatedSingletons_.length] =
               a);
      return a.instance_ = new a
    }
  };
  goog.instantiatedSingletons_ = [];
  goog.LOAD_MODULE_USING_EVAL = !0;
  goog.SEAL_MODULE_EXPORTS = !1;
  goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ = typeof Symbol === 'function' ?
      Symbol('preventModuleExportSealing') :
      null;
  goog.loadedModules_ = {};
  goog.DEPENDENCIES_ENABLED = !1;
  goog.ASSUME_ES_MODULES_TRANSPILED = !1;
  goog.TRUSTED_TYPES_POLICY_NAME = 'goog';
  goog.loadModule = function(a) {
    var b = goog.moduleLoaderState_;
    try {
      goog.moduleLoaderState_ = {
        moduleName: '',
        declareLegacyNamespace: !1,
        preventModuleExportSealing: !1,
        type: goog.ModuleType.GOOG
      };
      var c = {}, d = c;
      if (typeof a === 'function')
        d = a.call(void 0, d);
      else if (typeof a === 'string')
        d = goog.loadModuleFromSource_.call(void 0, d, a);
      else
        throw Error('Invalid module definition');
      var e = goog.moduleLoaderState_.moduleName;
      if (typeof e === 'string' && e) {
        if (goog.moduleLoaderState_.declareLegacyNamespace)
          a = c !== d, goog.constructNamespace_(e, d, a);
        else if (
            goog.SEAL_MODULE_EXPORTS && Object.seal && typeof d == 'object' &&
            d != null)
          if (goog.moduleLoaderState_.preventModuleExportSealing) {
            if (goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ &&
                Object.defineProperty)
              try {
                Object.defineProperty(
                    d, goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_,
                    {value: !0, writable: !1, enumerable: !1, configurable: !0})
              } catch (g) {
              }
          } else
            goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ &&
                    Object.prototype.hasOwnProperty.call(
                        d, goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_) ||
                Object.seal(d);
        var f = {
          exports: d,
          type: goog.ModuleType.GOOG,
          moduleId: goog.moduleLoaderState_.moduleName
        };
        goog.loadedModules_[e] = f
      } else
        throw Error('Invalid module name "' + e + '"');
    } finally {
      goog.moduleLoaderState_ = b
    }
  };
  goog.loadModuleFromSource_ = function(a) {
    eval(goog.CLOSURE_EVAL_PREFILTER_.createScript(arguments[1]));
    return a
  };
  goog.normalizePath_ = function(a) {
    a = a.split('/');
    for (var b = 0; b < a.length;)
      a[b] == '.'                                           ? a.splice(b, 1) :
          b && a[b] == '..' && a[b - 1] && a[b - 1] != '..' ? a.splice(--b, 2) :
                                                              b++;
    return a.join('/')
  };
  goog.loadFileSync_ = function(a) {
    if (goog.global.CLOSURE_LOAD_FILE_SYNC)
      return goog.global.CLOSURE_LOAD_FILE_SYNC(a);
    try {
      var b = new goog.global.XMLHttpRequest;
      b.open('get', a, !1);
      b.send();
      return b.status == 0 || b.status == 200 ? b.responseText : null
    } catch (c) {
      return null
    }
  };
  goog.typeOf = function(a) {
    var b = typeof a;
    return b != 'object' ? b : a ? Array.isArray(a) ? 'array' : b : 'null'
  };
  goog.isArrayLike = function(a) {
    var b = goog.typeOf(a);
    return b == 'array' || b == 'object' && typeof a.length == 'number'
  };
  goog.isDateLike = function(a) {
    return goog.isObject(a) && typeof a.getFullYear == 'function'
  };
  goog.isObject = function(a) {
    var b = typeof a;
    return b == 'object' && a != null || b == 'function'
  };
  goog.getUid = function(a) {
    return Object.prototype.hasOwnProperty.call(a, goog.UID_PROPERTY_) &&
        a[goog.UID_PROPERTY_] ||
        (a[goog.UID_PROPERTY_] = ++goog.uidCounter_)
  };
  goog.hasUid = function(a) {
    return !!a[goog.UID_PROPERTY_]
  };
  goog.removeUid = function(a) {
    a !== null && 'removeAttribute' in a &&
        a.removeAttribute(goog.UID_PROPERTY_);
    try {
      delete a[goog.UID_PROPERTY_]
    } catch (b) {
    }
  };
  goog.UID_PROPERTY_ = 'closure_uid_' + (Math.random() * 1E9 >>> 0);
  goog.uidCounter_ = 0;
  goog.cloneObject = function(a) {
    var b = goog.typeOf(a);
    if (b == 'object' || b == 'array') {
      if (typeof a.clone === 'function') return a.clone();
      if (typeof Map !== 'undefined' && a instanceof Map) return new Map(a);
      if (typeof Set !== 'undefined' && a instanceof Set) return new Set(a);
      b = b == 'array' ? [] : {};
      for (var c in a) b[c] = goog.cloneObject(a[c]);
      return b
    }
    return a
  };
  goog.bindNative_ = function(a, b, c) {
    return a.call.apply(a.bind, arguments)
  };
  goog.bindJs_ = function(a, b, c) {
    if (!a) throw Error();
    if (arguments.length > 2) {
      var d = Array.prototype.slice.call(arguments, 2);
      return function() {
        var e = Array.prototype.slice.call(arguments);
        Array.prototype.unshift.apply(e, d);
        return a.apply(b, e)
      }
    }
    return function() {
      return a.apply(b, arguments)
    }
  };
  goog.bind = function(a, b, c) {
    goog.TRUSTED_SITE && goog.FEATURESET_YEAR > 2012 ||
            Function.prototype.bind &&
                Function.prototype.bind.toString().indexOf('native code') !=
                    -1 ?
        goog.bind = goog.bindNative_ :
        goog.bind = goog.bindJs_;
    return goog.bind.apply(null, arguments)
  };
  goog.partial = function(a, b) {
    var c = Array.prototype.slice.call(arguments, 1);
    return function() {
      var d = c.slice();
      d.push.apply(d, arguments);
      return a.apply(this, d)
    }
  };
  goog.now = function() {
    return Date.now()
  };
  goog.globalEval = function(a) {
    (0, eval)(a)
  };
  goog.getCssName = function(a, b) {
    if (String(a).charAt(0) == '.')
      throw Error(
          'className passed in goog.getCssName must not start with ".". You passed: ' +
          a);
    var c = function(e) {
      return goog.cssNameMapping_[e] || e
    }, d = function(e) {
      e = e.split('-');
      for (var f = [], g = 0; g < e.length; g++) f.push(c(e[g]));
      return f.join('-')
    };
    d = goog.cssNameMapping_ ? goog.cssNameMappingStyle_ == 'BY_WHOLE' ? c : d :
                               function(e) {
                                 return e
                               };
    a = b ? a + '-' + d(b) : d(a);
    return goog.global.CLOSURE_CSS_NAME_MAP_FN ?
        goog.global.CLOSURE_CSS_NAME_MAP_FN(a) :
        a
  };
  goog.setCssNameMapping = function(a, b) {
    goog.cssNameMapping_ = a;
    goog.cssNameMappingStyle_ = b
  };
  goog.GetMsgOptions = function() {};
  goog.USE_GET_MSG_OVERRIDE = !1;
  goog.getMsg = function(a, b, c) {
    c && c.html && (a = a.replace(/</g, '&lt;'));
    c && c.unescapeHtmlEntities &&
        (a = a.replace(/&lt;/g, '<')
                 .replace(/&gt;/g, '>')
                 .replace(/&apos;/g, '\'')
                 .replace(/&quot;/g, '"')
                 .replace(/&amp;/g, '&'));
    b && (a = a.replace(/\{\$([^}]+)}/g, function(d, e) {
      return b != null && e in b ? b[e] : d
    }));
    return a
  };
  goog.getMsgWithFallback = function(a) {
    return a
  };
  goog.exportSymbol = function(a, b, c) {
    goog.exportPath_(a, b, !0, c)
  };
  goog.exportProperty = function(a, b, c) {
    a[b] = c
  };
  goog.weakUsage = function(a) {
    return a
  };
  goog.inherits = function(a, b) {
    function c() {}
    c.prototype = b.prototype;
    a.superClass_ = b.prototype;
    a.prototype = new c;
    a.prototype.constructor = a;
    a.base = function(d, e, f) {
      for (var g = Array(arguments.length - 2), h = 2; h < arguments.length;
           h++)
        g[h - 2] = arguments[h];
      return b.prototype[e].apply(d, g)
    }
  };
  goog.scope = function(a) {
    if (goog.isInModuleLoader_())
      throw Error('goog.scope is not supported within a module.');
    a.call(goog.global)
  };
  goog.identity_ = function(a) {
    return a
  };
  goog.createTrustedTypesPolicy = function(a) {
    var b = null, c = goog.global.trustedTypes;
    if (!c || !c.createPolicy) return b;
    try {
      b = c.createPolicy(a, {
        createHTML: goog.identity_,
        createScript: goog.identity_,
        createScriptURL: goog.identity_
      })
    } catch (d) {
      goog.logToConsole_(d.message)
    }
    return b
  };
  goog.CodeLocation = {DO_NOT_USE: '', DO_NOT_USE_ME_EITHER: '.'};
  goog.callerLocation = function() {
    return ''
  };
  goog.callerLocationIdInternalDoNotCallOrElse = function(a) {
    return a
  };
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info =
      {
        BUILD_CHANGELIST: '460000000',
        BUILD_TIMESTAMP: 1596240000,
        EXT_NAME: 'googlecloudtools.datacloud',
        EXT_VERSION: '1.2.0'
      };
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
      .ALLOWED_DATA_AGENT_SKILLS = new Set([
    'accidental_data_loss_prevention',
    'accidental-data-loss-prevention',
    'bigquery_ai_ml',
    'bigquery-ai-ml',
    'bigquery_bigframes',
    'bigquery-bigframes',
    'bigquery_data_transfer_service',
    'bigquery-data-transfer-service',
    'bigquery_graph_author',
    'bigquery-graph-author',
    'bigquery_graph_query',
    'bigquery-graph-query',
    'bigquery_observability',
    'bigquery-observability',
    'bigquery_optimization',
    'bigquery-optimization',
    'bigquery_troubleshooting',
    'bigquery-troubleshooting',
    'bigtable_basics',
    'bigtable-basics',
    'building_data_apps',
    'building-data-apps',
    'cloud_databases_onboarding',
    'cloud-databases-onboarding',
    'data_autocleaning',
    'data-autocleaning',
    'dataform_bigquery',
    'dataform-bigquery',
    'dbt_bigquery',
    'dbt-bigquery',
    'discovering_gcp_data_assets',
    'discovering-gcp-data-assets',
    'enforcing_resource_attribution',
    'enforcing-resource-attribution',
    'federate_lakehouse_catalog',
    'federate-lakehouse-catalog',
    'gcp_composer_troubleshooting',
    'gcp-composer-troubleshooting',
    'gcp_dataflow',
    'gcp-dataflow',
    'gcp_data_pipelines',
    'gcp-data-pipelines',
    'gcp_managed_airflow_dag_authoring',
    'gcp-managed-airflow-dag-authoring',
    'gcp_managed_airflow_migrations',
    'gcp-managed-airflow-migrations',
    'gcp_managed_airflow_recommendations',
    'gcp-managed-airflow-recommendations',
    'gcp_managed_spark_upgrades',
    'gcp-managed-spark-upgrades',
    'gcp_pipeline_orchestration',
    'gcp-pipeline-orchestration',
    'gcp_pipeline_resource_provisioning',
    'gcp-pipeline-resource-provisioning',
    'gcp_spark',
    'gcp-spark',
    'gcp_spark_observability',
    'gcp-spark-observability',
    'gcp_spark_troubleshooting',
    'gcp-spark-troubleshooting',
    'gcs_security_assessment',
    'gcs-security-assessment',
    'google_cloud_storage_basics',
    'google-cloud-storage-basics',
    'google_cloud_storage_bucket_architect',
    'google-cloud-storage-bucket-architect',
    'google_cloud_storage_fuse',
    'google-cloud-storage-fuse',
    'managing_python_dependencies',
    'managing-python-dependencies',
    'ml_best_practices',
    'ml-best-practices',
    'notebook_guidance',
    'notebook-guidance',
    'schema_mapping',
    'schema-mapping'
  ]);
  var module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types =
      {
        InjectionKey: class {
          constructor(a) {
            this.id = a
          }
        }
      };
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_ProviderConfig() {
  }
  module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
      .ProviderConfig =
      module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_ProviderConfig;
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey(
      a) {
    return a instanceof
                module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
                    .InjectionKey ||
            a && typeof a === 'object' && 'id' in a ?
        a.id :
        a
  }
  module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
      .getMapKey =
      module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey;
  var module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector =
      {};
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector_getTokenDisplayName(
      a) {
    return a instanceof
                module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
                    .InjectionKey ||
            a && typeof a === 'object' && 'id' in a ?
        a.id :
        a.name || 'UnknownConstructor'
  }
  module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector
      .Injector = class {
    constructor(a) {
      this.singletons = new Map;
      this.providers = new Map;
      this.currentlyExecutingGetOperations = [];
      for (let b of a) {
        a = module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey(
            b.key);
        if (this.providers.has(a))
          throw Error(`Two providers registered for key: ${
              module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector_getTokenDisplayName(
                  b.key)}`);
        this.providers.set(a, b)
      }
    }
    addProvider(a) {
      var b =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey(
              a.key);
      if (this.providers.has(b))
        throw Error(`Two providers registered for key: ${
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector_getTokenDisplayName(
                a.key)}`);
      this.providers.set(b, a)
    }
    get(a) {
      var b =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey(
              a);
      if (this.currentlyExecutingGetOperations.includes(b))
        throw a = [...this.currentlyExecutingGetOperations, b],
              a = a.map(
                  c => typeof c === 'function' ?
                      c.name || 'UnknownConstructor' :
                      String(c)),
              Error(`Circular dependency detected: ${a.join(' -> ')}`);
      this.currentlyExecutingGetOperations.push(b);
      try {
        return this.getInternal(a)
      } finally {
        this.currentlyExecutingGetOperations.pop()
      }
    }
    getInternal(a) {
      var b = module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types_getMapKey(
              a),
          c = this.singletons.get(b);
      if (c) return c;
      c = this.providers.get(b);
      if (!c)
        throw Error(`Provider not found for key: ${
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector_getTokenDisplayName(
                a)}`);
      a = c.factory();
      this.singletons.set(b, a);
      return a
    }
  };
  const module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_globalInjector =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$injector
          .Injector([]);
  let module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_globalInjectorForTesting =
      null;
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_getGlobalInjector() {
    var a;
    return (a = module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_globalInjectorForTesting) !=
            null ?
        a :
        module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_globalInjector
  }
  const
      module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addedProvidersInDebug =
          [];
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      a) {
    var b =
        module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_getGlobalInjector();
    if (a.length > 0)
      for (let c of a)
        b.addProvider(c),
            typeof goog !== 'undefined' && goog.DEBUG &&
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addedProvidersInDebug
                .push(c)
  }
  function
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
      a) {
    return module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_getGlobalInjector()
        .get(a)
  };
  var module$exports$third_party$javascript$typings$node$node$child_process =
      (typeof require === 'function' ? require : function() {
        return {}
      })('child_process');
  var module$exports$third_party$javascript$typings$node$node$fs =
      (typeof require === 'function' ? require : function() {
        return {}
      })('fs');
  var module$exports$third_party$javascript$typings$node$node$os =
      (typeof require === 'function' ? require : function() {
        return {}
      })('os');
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers =
      {};
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .IS_LOCAL_TELEMETRY =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:is-local-telemetry');
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .SPAWN_FN =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:spawn-fn');
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .PROCESS_ENV =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:process-env');
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_OsDeps() {
  }
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .OsDeps =
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_OsDeps;
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .EXEC_SYNC_FN =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:exec-sync-fn');
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .OS_DEPS =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:os-deps');
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_FsDeps() {
  }
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .FsDeps =
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_FsDeps;
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .FS_DEPS =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/common_providers.ts:fs-deps');
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_setupCommonProviders(
      a) {
    module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
        [
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .IS_LOCAL_TELEMETRY,
            factory: () => a.isLocalTelemetry
          },
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .SPAWN_FN,
            factory: () =>
                module$exports$third_party$javascript$typings$node$node$child_process
                    .spawn
          },
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .PROCESS_ENV,
            factory: () => process
          },
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .FS_DEPS,
            factory: () =>
                module$exports$third_party$javascript$typings$node$node$fs
          },
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .EXEC_SYNC_FN,
            factory: () =>
                module$exports$third_party$javascript$typings$node$node$child_process
                    .execSync
          },
          {
            key:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .OS_DEPS,
            factory: () =>
                module$exports$third_party$javascript$typings$node$node$os
          }
        ])
  }
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
      .setupCommonProviders =
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_setupCommonProviders;
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
      a, b) {
    process.env.DATACLOUD_HOOK_DEBUG === 'true' &&
        (b ? (b = b instanceof Error ? b.message : String(b),
              console.error(`[TelemetryHook] ${a}: ${b}`)) :
             console.error(`[TelemetryHook] ${a}`))
  };
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
      a) {
    return typeof a === 'object' && a !== null && !Array.isArray(a)
  }
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isNonEmptyString(
      a) {
    return typeof a === 'string' && a.length > 0
  };
  var module$exports$third_party$javascript$typings$node$node$crypto =
      (typeof require === 'function' ? require : function() {
        return {}
      })('crypto');
  var module$exports$third_party$javascript$typings$node$node$path =
      (typeof require === 'function' ? require : function() {
        return {}
      })('path');
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$file_cache = {
    FileCache: class {
      constructor() {
        this.fs =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .FS_DEPS);
        this.os =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .OS_DEPS)
      }
      getOrRefresh(a, b, c) {
        a = module$exports$third_party$javascript$typings$node$node$path
                .join(this.os.tmpdir(), 'datacloud_telemetry', `${a}.json`);
        try {
          let d = JSON.parse(this.fs.readFileSync(a, 'utf8'));
          if (module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                  d) &&
              typeof d.fetchedAtMs === 'number' &&
              Date.now() - d.fetchedAtMs >= 0 &&
              Date.now() - d.fetchedAtMs < b &&
              (d.value === null || typeof d.value === 'string')) {
            let e;
            return (e = d.value) != null ? e : void 0
          }
        } catch (d) {
        }
        b = c();
        try {
          let d = `${a}.${
              module$exports$third_party$javascript$typings$node$node$crypto
                  .randomUUID()}`;
          this.fs.mkdirSync(
              module$exports$third_party$javascript$typings$node$node$path
                  .dirname(a),
              {recursive: !0});
          let e;
          this.fs.writeFileSync(
              d,
              JSON.stringify(
                  {value: (e = b) != null ? e : null, fetchedAtMs: Date.now()}),
              {encoding: 'utf8'});
          this.fs.renameSync(d, a)
        } catch (d) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              `Failed to write cache ${a}`, d)
        }
        return b
      }
    }
  };
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [{
        key:
            module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$file_cache
                .FileCache,
        factory: () =>
            new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$file_cache
                .FileCache
      }]);
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser =
      {};
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_McpInfo() {
  }
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
      .McpInfo =
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_McpInfo;
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
      .GOOGLE_MCP_SERVERS =
      'notebook notebooks visualization data-agent-kit alloydb alloydb-postgres alloydb-postgres-admin bigquery bigtable bigtable-admin bigtable-data spanner cloud-sql cloud-sql-postgresql cloud-sql-postgresql-admin cloud-sql-mysql cloud-sql-mysql-admin cloud-sql-sqlserver cloud-sql-sqlserver-admin composer dataform dataproc dform serverless-spark firestore knowledge_catalog gcs cloud-storage'
          .split(' ');
  const
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_GOOGLE_MCP_SERVERS_REGEX =
          new RegExp(`(^|[_-])(${
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
                  .GOOGLE_MCP_SERVERS.join('|')})(_(remote|toolbox))?$`),
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_DAK_MCP_SERVER_REGEX =
          /(^|[_-])dak-/,
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_KNOWN_GOOGLE_SERVERS =
          'datacloud_knowledge_catalog_remote datacloud_bigtable-admin_remote datacloud_bigtable-data_remote datacloud_bigquery_remote datacloud_composer_remote datacloud_dataproc_remote datacloud_dform_remote datacloud_cloud-sql_remote datacloud_spanner_remote datacloud_firestore_remote datacloud_alloydb_remote datacloud_gcs_remote visualization notebooks notebook dak-data-agent-kit dak-bigtable-data dak-notebook dak-dataform dak-bigquery dak-bigtable dak-cloudsql dak-composer dak-firestore dak-alloydb dak-spanner dak-spark dak-gcs dak-kc'
              .split(' ')
              .sort((a, b) => b.length - a.length);
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
      .VSCODE_MCP_SERVER_PREFIX_MAP = {
    mcp_notebooks_: 'notebooks',
    mcp_visualization_: 'visualization',
    'mcp_data-agent-ki_': 'data-agent-kit',
    mcp_datacloud_all_: 'datacloud_alloydb',
    mcp_datacloud_big_: 'datacloud_bigquery',
    mcp_datacloud_spa_: 'datacloud_spanner',
    mcp_datacloud_clo_: 'datacloud_cloud-sql',
    mcp_datacloud_com_: 'datacloud_composer',
    mcp_datacloud_dat_: 'datacloud_dataproc',
    mcp_datacloud_dfo_: 'datacloud_dform',
    mcp_datacloud_ser_: 'datacloud_serverless-spark',
    mcp_datacloud_kno_: 'datacloud_knowledge_catalog',
    mcp_datacloud_gcs_: 'datacloud_gcs',
    mcp_datacloud_fir_: 'datacloud_firestore'
  };
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
      .McpParser = class {
    parseMcpInfo(a) {
      var b = a.tool_name;
      if (!module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isNonEmptyString(
              b) ||
          !b.startsWith('MCP:')) {
        b = a.mcp_server_name;
        var c = a.tool_name;
        b = module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isNonEmptyString(
                b) &&
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isNonEmptyString(
                    c) ?
            {
              serverName: b,
              toolName: c,
              isGoogleTool:
                  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_isGoogleMcpServer(
                      b)
            } :
            void 0;
        if (!b)
          a: {
            b = a;
            if (b.toolCall &&
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                    b.toolCall) &&
                (b = b.toolCall,
                 b.name === 'call_mcp_tool' && b.args &&
                     module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                         b.args) &&
                     (c = b.args, b = c.ServerName, c = c.ToolName,
                      typeof b === 'string' && b && typeof c === 'string' &&
                          c))) {
              b = {
                serverName: b,
                toolName: c,
                isGoogleTool:
                    module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_isGoogleMcpServer(
                        b)
              };
              break a
            } b = void 0
          } if (!b) a: {
            if ('tool_name' in a &&
                (b = a.tool_name,
                 typeof b === 'string' &&
                     b.startsWith(
                         'mcp_'))) for (let [f, g] of Object
                                            .entries(
                                                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
                                                    .VSCODE_MCP_SERVER_PREFIX_MAP)) {
              var d = f;
              c = g;
              if (b.startsWith(d) && (d = b.substring(d.length))) {
                b = {serverName: c, toolName: d, isGoogleTool: !0};
                break a
              }
            } b = void 0
          } if (!b) a: {
            if ('tool_name' in a &&
                (b = a.tool_name,
                 typeof b === 'string' &&
                     (c = b.split('__'),
                      c.length >= 2 &&
                          (b = c[c.length - 2], c = c[c.length - 1],
                           b && c)))) {
              b = {
                serverName: b,
                toolName: c,
                isGoogleTool:
                    module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_isGoogleMcpServer(
                        b)
              };
              break a
            } b = void 0
          } if (!b) a: {
            a = a.toolName; if (typeof a === 'string') {
              for (
                  var e of
                      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_KNOWN_GOOGLE_SERVERS)
                if (b = `${e}-`, c = a.indexOf(b),
                    c === 0 || c > 0 && (a[c - 1] === '_' || a[c - 1] === '-'))
                  if (b = a.substring(c + b.length)) {
                    b = {serverName: e, toolName: b, isGoogleTool: !0};
                    break a
                  }
              e = a.lastIndexOf('-');
              if (!(e <= 0 || e === a.length - 1)) {
                b = a.substring(0, e);
                b = {
                  serverName: b,
                  toolName: a.substring(e + 1),
                  isGoogleTool:
                      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_isGoogleMcpServer(
                          b)
                };
                break a
              }
            } b = void 0
          } return b
      }
    }
  };
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_isGoogleMcpServer(
      a) {
    return module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_KNOWN_GOOGLE_SERVERS
               .includes(a) ||
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_DAK_MCP_SERVER_REGEX
            .test(a) ||
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser_GOOGLE_MCP_SERVERS_REGEX
            .test(a)
  }
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [{
        key:
            module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
                .McpParser,
        factory: () =>
            new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
                .McpParser
      }]);
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver =
      {GCLOUD_PROJECT_CACHE_TTL_MS: 6E5};
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver
      .ProjectResolver = class {
    constructor() {
      this.execSync =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .EXEC_SYNC_FN);
      this.fs =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .FS_DEPS);
      this.os =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .OS_DEPS);
      this.processEnv =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .PROCESS_ENV);
      this.cache =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$file_cache
                  .FileCache)
    }
    resolveProject() {
      return this.getDakConfigProject() || this.getGcloudProject()
    }
    getDakConfigProject() {
      try {
        let b =
            module$exports$third_party$javascript$typings$node$node$path
                .join(
                    this.getHomeDir(), '.config', 'data-agent-kit',
                    'config.json');
        if (this.fs.existsSync(b)) {
          var a = JSON.parse(this.fs.readFileSync(b, 'utf8'));
          if (module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                  a) &&
              typeof a.projectId === 'string')
            return a.projectId.trim() || void 0
        }
      } catch (b) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            'Failed to read Data Agent Kit config.json', b)
      }
    }
    getGcloudProject() {
      return this.cache.getOrRefresh(
          'gcloud_project',
          module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver
              .GCLOUD_PROJECT_CACHE_TTL_MS,
          () => this.queryGcloudProject())
    }
    queryGcloudProject() {
      try {
        let a = this.execSync(
            'gcloud config get-value project --quiet --verbosity=none', {
              encoding: 'utf8',
              stdio: ['ignore', 'pipe', 'ignore'],
              timeout: 5E3,
              env: {
                ...this.processEnv.env,
                CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK: '1'
              }
            });
        return String(a).trim() || void 0
      } catch (a) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            'Failed to get active project from gcloud', a)
      }
    }
    getHomeDir() {
      return this.processEnv.env.HOME || this.os.homedir()
    }
  };
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [{
        key:
            module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver
                .ProjectResolver,
        factory: () =>
            new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver
                .ProjectResolver
      }]);
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser =
      {};
  const
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_SKILL_FILE_REGEX =
          /[/\\]skills[/\\]([^/\\]+)[/\\]SKILL\.md$/i;
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_SkillInfo() {
  }
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
      .SkillInfo =
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_SkillInfo;
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
      .ALLOWED_SKILLS =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/skill_parser.ts:allowed-skills');
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
      .SkillParser = class {
    constructor() {
      this.fileSystem =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .FS_DEPS);
      this.allowedSkills =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
                  .ALLOWED_SKILLS)
    }
    parseSkillInfo(a) {
      try {
        a: {
          if (a.toolCall &&
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                  a.toolCall)) {
            let c = a.toolCall;
            if ('args' in c) {
              var b =
                  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_parseRecord(
                      c.args);
              break a
            }
          } b = 'tool_input' in a ?
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_parseRecord(
                  a.tool_input) :
              'toolArgs' in a ?
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_parseRecord(
                  a.toolArgs) :
              void 0
        } return b ?
            this.parseSkillToolArgs(b) || this.parseCommandToolArgs(b) ||
                this.parseFileToolArgs(b) :
            void 0
      } catch (c) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            'Failed to parse skill info', c)
      }
    }
    parseSkillToolArgs(a) {
      var b = a.skill || a.command;
      if (typeof b === 'string' && b) {
        var c;
        b.startsWith('dak:') ?
            c = b.substring(4) :
            typeof a.skill !== 'string' || b.includes(':') || (c = b);
        if (c) return a = c.toLowerCase(), {
            skillName: a, isGooglePublisher: this.allowedSkills.has(a)
          }
      }
    }
    parseCommandToolArgs(a) {
      if (typeof a.command === 'string' && a.command &&
          (a = a.command,
           a = module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_splitCommandArgs(
               a),
           a = a.find(
               b =>
                   module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_SKILL_FILE_REGEX
                       .test(b))))
        return this.parseSkillFilePath(a)
    }
    parseFileToolArgs(a) {
      a = a.filePath || a.AbsolutePath || a.file_path;
      if (typeof a === 'string' && a) return this.parseSkillFilePath(a)
    }
    parseSkillFilePath(a) {
      var b =
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_getSkillName(
              a);
      if (b) return a = this.isGoogleSkillFile(a), {
          skillName: b, isGooglePublisher: a
        }
    }
    isGoogleSkillFile(a) {
      try {
        let b =
            module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_getSkillName(
                a);
        if (!b || !this.allowedSkills.has(b) || !this.fileSystem.existsSync(a))
          return !1;
        let c = this.fileSystem.readFileSync(a, 'utf8'),
            d = c.match(/^---\r?\n([\s\S]*?)\r?\n---/);
        if (!d) return !1;
        let e = d[1];
        return /^[ \t]*(publisher|producer)[ \t]*:[ \t]*['"]?google['"]?[ \t]*$/im
            .test(e)
      } catch (b) {
        return module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                   'Failed to check if Google skill file', b),
               !1
      }
    }
  };
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_getSkillName(
      a) {
    return (a = a.match(
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_SKILL_FILE_REGEX)) ?
        a[1].toLowerCase() :
        void 0
  }
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_parseRecord(
      a) {
    if (typeof a === 'string') try {
        let b = JSON.parse(a);
        if (module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                b))
          return b
      } catch {
      }
    else if (
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
            a))
      return a
  }
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser_splitCommandArgs(
      a) {
    var b = [], c = '', d = !1, e = !1;
    for (let f = 0; f < a.length; f++) {
      let g = a[f];
      g !== '"' || e ? g !== '\'' || d ?
                       g !== ' ' || d || e ? c += g : c && (b.push(c), c = '') :
                       e = !e :
                       d = !d
    }
    c && b.push(c);
    return b
  }
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [
        {
          key:
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
                  .ALLOWED_SKILLS,
          factory: () =>
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
                  .ALLOWED_DATA_AGENT_SKILLS
        },
        {
          key:
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
                  .SkillParser,
          factory: () =>
              new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
                  .SkillParser
        }
      ]);
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$user_identity = {
    UserIdentityResolver: class {
      constructor() {
        this.execSync =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .EXEC_SYNC_FN);
        this.fs =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .FS_DEPS);
        this.os =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .OS_DEPS);
        this.processEnv =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .PROCESS_ENV)
      }
      getGcloudEmail() {
        try {
          let a = this.getGoogleCloudToolsAuthFolder(),
              b = module$exports$third_party$javascript$typings$node$node$path
                      .join(a, 'credentials.json');
          if (this.fs.existsSync(b)) {
            let c = this.fs.readFileSync(b, 'utf8'), d = JSON.parse(c);
            if (d && typeof d === 'object' && typeof d.email === 'string' &&
                d.email.trim())
              return d.email.trim()
          }
        } catch (a) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Failed to read cached credentials', a)
        }
        try {
          let a =
              this.execSync(
                      'gcloud config get-value account',
                      {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']})
                  .trim();
          if (a) return a
        } catch (a) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Failed to get active account from gcloud', a)
        }
      }
      getInstallId() {
        try {
          let a = this.getCloudCodeAppDataDir(),
              b = module$exports$third_party$javascript$typings$node$node$path
                      .join(a, 'install_id.txt');
          if (this.fs.existsSync(b)) {
            let c = this.fs.readFileSync(b, 'utf8').trim();
            if (c) return c
          }
          return this.generateAndPersistInstallId(a, b)
        } catch (a) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Failed to read or create install ID', a)
        }
      }
      generateAndPersistInstallId(a, b) {
        try {
          this.fs.mkdirSync(a, {recursive: !0});
          let c =
              module$exports$third_party$javascript$typings$node$node$crypto
                  .randomUUID();
          a = `${b}.${c}.deleteme`;
          this.fs.writeFileSync(a, c, {encoding: 'utf8'});
          try {
            return this.fs.linkSync(a, b), c
          } catch (d) {
            let e, f = (e = d) == null ? void 0 : e.code;
            if (f === 'EEXIST' && this.fs.existsSync(b)) {
              let g = this.fs.readFileSync(b, 'utf8').trim();
              if (g) return g
            }
            throw d;
          } finally {
            try {
              this.fs.unlinkSync(a)
            } catch (d) {
            }
          }
        } catch (c) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Failed to generate or persist install ID', c)
        }
      }
      resolveIdentity() {
        var a = this.getGcloudEmail();
        if (a) return {email: a};
        if (a = this.getInstallId()) return {
            installId: a
          }
      }
      isTelemetryEnabled() {
        try {
          let a = this.processEnv.env.DO_NOT_TRACK;
          if (a === '1' || a === 'true') return !1;
          let b = this.os.homedir(),
              c = module$exports$third_party$javascript$typings$node$node$path
                      .join(b, '.data_agent_kit', 'config.json'),
              d = this.loadConfig(c);
          return d.enableTelemetry !== !1
        } catch (a) {
          return module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                     'Failed to check if telemetry is enabled. Defaulting to enabled',
                     a),
                 !0
        }
      }
      loadConfig(a) {
        try {
          if (this.fs.existsSync(a)) {
            let b = this.fs.readFileSync(a, 'utf8').trim();
            if (b) {
              let c = JSON.parse(b);
              if (module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                      c))
                return c
            }
          }
        } catch (b) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              `Failed to read or parse config file at ${a}`, b)
        }
        return {}
      }
      getBaseAppDataDir(a) {
        var b = this.processEnv.env.HOME || this.os.homedir();
        switch (this.processEnv.platform) {
          case 'linux':
            return module$exports$third_party$javascript$typings$node$node$path
                .join(b, '.cache', a);
          case 'win32':
            return module$exports$third_party$javascript$typings$node$node$path
                .join(
                    this.processEnv.env.LOCALAPPDATA ||
                        module$exports$third_party$javascript$typings$node$node$path
                            .join(b, 'AppData', 'Local'),
                    a);
          case 'darwin':
            return module$exports$third_party$javascript$typings$node$node$path
                .join(b, 'Library', 'Application Support', a);
          default:
            return module$exports$third_party$javascript$typings$node$node$path
                .join(this.os.tmpdir(), a)
        }
      }
      getGoogleCloudToolsAuthFolder() {
        return module$exports$third_party$javascript$typings$node$node$path
            .join(this.getBaseAppDataDir('google-cloud-tools'), 'auth')
      }
      getCloudCodeAppDataDir() {
        return this.getBaseAppDataDir('cloud-code')
      }
    }
  };
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [{
        key:
            module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$user_identity
                .UserIdentityResolver,
        factory: () =>
            new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$user_identity
                .UserIdentityResolver
      }]);
  var module$exports$cloud$developer_experience$datacloud_vscode$common$telemetry$constants = {
    OnboardingEvent: {
      EXTENSION_ACTIVATE_START:
          'google.datacloud.onboarding.extension.activateStart',
      EXTENSION_ACTIVATE_COMPLETE:
          'google.datacloud.onboarding.extension.activateComplete',
      LOGIN: 'google.datacloud.onboarding.login.initiate',
      FIRST_TIME_INSTALL:
          'google.datacloud.onboarding.extension.firstTimeInstall',
      ALREADY_LOGGED_IN: 'google.datacloud.auth.login.already',
      ONBOARDING_COMPLETE: 'google.datacloud.onboarding.journey.complete',
      STEP: 'google.datacloud.onboarding.step',
      ACTIVE_ONBOARDED_USER: 'google.datacloud.onboarding.activeUser.report'
    },
    OnboardingServicesEvent: {
      PAGE_VIEW: 'google.datacloud.onboarding.services.view',
      NEXT: 'google.datacloud.onboarding.services.next',
      SKILLS_SYNC: 'google.datacloud.onboarding.services.skills.sync',
      MCP_SYNC: 'google.datacloud.onboarding.services.mcp.sync',
      FETCH_ENABLED_APIS:
          'google.datacloud.onboarding.services.enabledApis.fetch',
      ENABLE_APIS: 'google.datacloud.onboarding.services.apis.enable'
    },
    OnboardingMissingRolesEvent: {
      PAGE_VIEW: 'google.datacloud.onboarding.missingRoles.view',
      COPY_LIST: 'google.datacloud.onboarding.missingRoles.copyList',
      EMAIL_LIST: 'google.datacloud.onboarding.missingRoles.emailList',
      BACK: 'google.datacloud.onboarding.missingRoles.back',
      NEXT: 'google.datacloud.onboarding.missingRoles.next'
    },
    OnboardingCommand: {
      SHOW_ONBOARDING: 'google.datacloud.showOnboarding',
      RESET_ONBOARDING: 'google.datacloud.resetOnboarding',
      HANDLE_LOGIN_OR_ONBOARDING: 'google.datacloud.handleLoginOrOnboarding',
      OPEN_SELECT_SERVICES: 'google.datacloud.onboarding.services.open',
      ENABLE_SERVICE_INTEGRATION:
          'google.datacloud.onboarding.services.enableIntegration'
    },
    QuickstartEvent: {
      GET_STARTED: 'google.datacloud.quickstart.guide.start',
      SHOW_SKILLS: 'google.datacloud.quickstart.skills.show',
      OPEN_URL: 'google.datacloud.quickstart.url.open',
      COPY_PROMPT: 'google.datacloud.quickstart.prompt.copy'
    },
    QuickstartCommand:
        {OPEN_QUICK_START_GUIDE: 'google.datacloud.quickStartGuide'},
    NotebookEvent: {
      CREATE_NOTEBOOK: 'google.datacloud.notebook.create',
      CELL_EXECUTE: 'google.datacloud.notebook.cell.execute',
      SQL_CELL_EXECUTE: 'google.datacloud.notebook.sqlCell.execute',
      MAGIC_SQL_CELL_EXECUTE: 'google.datacloud.notebook.magicSqlCell.execute'
    },
    NotebookCommand: {
      ADD_BIGQUERY_MAGIC_SQL_CELL:
          'google.datacloud.notebook.addBigQueryMagicSqlCell'
    },
    GcsEvent: {
      EXPLORER_EXPAND: 'google.datacloud.gcs.explorer.expand',
      EXPLORER_FETCH: 'google.datacloud.gcs.explorer.fetch',
      DRAG_AND_DROP_DRAG: 'google.datacloud.gcs.dragAndDrop.drag',
      DRAG_AND_DROP_DROP: 'google.datacloud.gcs.dragAndDrop.drop'
    },
    GcsCommand: {
      EXPLORER_REFRESH: 'google.datacloud.cloudStorage.refreshExplorer',
      BUCKET_CREATE: 'google.datacloud.createGcsBucket',
      FOLDER_CREATE: 'google.datacloud.gcs.folder.create',
      RESOURCE_RENAME: 'google.datacloud.gcs.resource.rename',
      RESOURCE_DELETE: 'google.datacloud.gcs.resource.delete',
      RESOURCE_DOWNLOAD: 'google.datacloud.gcs.resource.download',
      RESOURCE_UPLOAD: 'google.datacloud.gcs.resource.upload',
      FILTER: 'google.datacloud.cloudStorage.filter',
      FILTER_ACTIVE: 'google.datacloud.cloudStorage.filterActive',
      RENAME_GCS_FILE: 'google.datacloud.renameGcsFile',
      RENAME_GCS_FOLDER: 'google.datacloud.renameGcsFolder',
      DELETE_GCS_FILE: 'google.datacloud.deleteGcsFile',
      DELETE_GCS_FOLDER: 'google.datacloud.deleteGcsFolder',
      CREATE_BUCKET_GCS_FOLDER: 'google.datacloud.createBucketGcsFolder',
      CREATE_GCS_FOLDER: 'google.datacloud.createGcsFolder',
      DOWNLOAD_GCS_FILE: 'google.datacloud.downloadGcsFile',
      UPLOAD_GCS_FILE: 'google.datacloud.uploadGcsFile',
      UPLOAD_BUCKET_GCS_FILE: 'google.datacloud.uploadBucketGcsFile',
      OPEN_GCS_FILE: 'google.datacloud.openGcsFile',
      LOAD_IN_SPARK_NOTEBOOK:
          'google.datacloud.cloudStorage.loadInSparkNotebook',
      COPY_GCS_PATH: 'google.datacloud.copyGcsPath'
    },
    CatalogEvent: {
      EXPLORER_EXPAND: 'google.datacloud.dataplex.explorer.expand',
      EXPLORER_LOAD_MORE: 'google.datacloud.dataplex.explorer.loadMore',
      EXPLORER_FETCH_DURATION:
          'google.datacloud.dataplex.explorer.fetchDuration',
      EXPLORER_CHECK_REFERENCE_UNSUPPORTED:
          'google.datacloud.dataplex.explorer.checkReferenceUnsupported',
      EXPLORER_CHECK_REFERENCE_FAILED:
          'google.datacloud.dataplex.explorer.checkReferenceFailed',
      CATALOG_OPEN_DETAILS: 'google.datacloud.dataplex.catalog.openDetails',
      PAGE_IMPRESSION: 'google.datacloud.dataplex.catalog.details.impression',
      TAB_CLICK: 'google.datacloud.dataplex.catalog.details.tabClick',
      FETCH_INSIGHTS: 'google.datacloud.dataplex.catalog.details.fetchInsights',
      FETCH_ENTRY_LINKS:
          'google.datacloud.dataplex.catalog.details.fetchEntryLinks',
      FETCH_GRAPH_METADATA:
          'google.datacloud.dataplex.catalog.details.fetchGraphMetadata',
      PREVIEW_LOAD: 'google.datacloud.dataplex.resource.preview.load',
      RESOURCE_COPY_ID: 'google.datacloud.dataplex.resource.copyId',
      RESOURCE_INSERT_AT_CURSOR:
          'google.datacloud.dataplex.resource.insertAtCursor',
      EDITOR_RESOLVE: 'google.datacloud.dataplex.editor.resolve',
      GRAPH_RENDER: 'google.datacloud.dataplex.graph.render',
      INSIGHTS_QUERY_TOGGLE: 'google.datacloud.dataplex.insights.query.toggle',
      INSIGHTS_QUERY_OPEN: 'google.datacloud.dataplex.insights.query.open',
      INSIGHTS_QUERY_COPY: 'google.datacloud.dataplex.insights.query.copy',
      LINEAGE_LOAD: 'google.datacloud.dataplex.lineage.load',
      LINEAGE_TAB_TOGGLE: 'google.datacloud.dataplex.lineage.tab.toggle',
      LINEAGE_GRAPH_EXPAND: 'google.datacloud.dataplex.lineage.graph.expand',
      LINEAGE_GRAPH_NODE_OPEN_DETAILS:
          'google.datacloud.dataplex.lineage.graph.node.openDetails',
      LINEAGE_GRAPH_SCHEMA_TOGGLE:
          'google.datacloud.dataplex.lineage.graph.schema.toggle',
      LINEAGE_LIST_ROW_CLICK:
          'google.datacloud.dataplex.lineage.list.row.click',
      DATA_PROFILE_LOAD: 'google.datacloud.dataplex.dataProfile.load',
      DATA_PROFILE_COLUMN_TOGGLE:
          'google.datacloud.dataplex.dataProfile.column.toggle',
      DATA_QUALITY_LOAD: 'google.datacloud.dataplex.dataQuality.load',
      DATA_QUALITY_COLUMN_TOGGLE:
          'google.datacloud.dataplex.dataQuality.column.toggle',
      GRAPH_FIT_TO_VIEW: 'google.datacloud.dataplex.graph.fitToView',
      GRAPH_RELOAD: 'google.datacloud.dataplex.graph.reload',
      GRAPH_NODE_SELECT: 'google.datacloud.dataplex.graph.node.select',
      GRAPH_NODE_EXPAND: 'google.datacloud.dataplex.graph.node.expand',
      GRAPH_EDGE_SELECT: 'google.datacloud.dataplex.graph.edge.select',
      GRAPH_LABEL_SELECT: 'google.datacloud.dataplex.graph.label.select',
      GRAPH_OPEN_SCHEMA: 'google.datacloud.dataplex.graph.schema.open',
      GRAPH_NODE_DRAG_END: 'google.datacloud.dataplex.graph.node.dragEnd',
      GRAPH_LEGEND_TOGGLE: 'google.datacloud.dataplex.graph.legend.toggle',
      ZERO_STATE_PANTHEON_LINK_CLICK:
          'google.datacloud.dataplex.zeroState.pantheonLink.click',
      DRAG_AND_DROP_DRAG: 'google.datacloud.dataplex.catalog.drag',
      DRAG_AND_DROP_DROP: 'google.datacloud.dataplex.catalog.drop',
      TABLE_SCHEMA_VIEW: 'google.datacloud.dataplex.ui.table.schema.view',
      INTEGRATION_WARNING_CHECK:
          'google.datacloud.dataplex.integrationWarning.check',
      INTEGRATION_WARNING_SHOW:
          'google.datacloud.dataplex.integrationWarning.show',
      INTEGRATION_WARNING_CLICK:
          'google.datacloud.dataplex.integrationWarning.click',
      QUERY_OPEN: 'google.datacloud.dataplex.query.open',
      CLOUDSQL_PUBLIC_SCHEMA_INJECTION_FAIL:
          'google.datacloud.dataplex.explorer.cloudsql.publicSchema.injection.fail',
      CLOUDSQL_PUBLIC_SCHEMA_INJECT:
          'google.datacloud.dataplex.explorer.cloudsql.publicSchema.injection.inject',
      ALLOYDB_PUBLIC_SCHEMA_INJECTION_FAIL:
          'google.datacloud.dataplex.explorer.alloydb.publicSchema.injection.fail',
      ALLOYDB_PUBLIC_SCHEMA_INJECT:
          'google.datacloud.dataplex.explorer.alloydb.publicSchema.injection.inject',
      SEARCH_RESULT_OPENED: 'searchResultOpened',
      SEARCH_RESULT_LOADED: 'searchResultLoaded',
      SEARCH_FAILED: 'searchFailed',
      SEARCH_INITIATED: 'searchInitiated',
      SEARCH_QUERY_MODIFIED: 'searchQueryModified',
      SEARCH_FILTERS_ADDED: 'searchFiltersAdded',
      SEARCH_FILTERS_REMOVED: 'searchFiltersRemoved',
      RESOURCE_QUERY_ACTIONS_OPEN_DATA_WRANGLER:
          'dataplex.resource_query_actions.open_data_wrangler',
      RESOURCE_QUERY_ACTIONS_OPEN_QUERY_IN_EDITOR:
          'dataplex.resource_query_actions.open_query_in_editor',
      RESOURCE_QUERY_ACTIONS_LOAD_IN_BIGFRAMES_NOTEBOOK:
          'dataplex.resource_query_actions.load_in_bigframes_notebook',
      RESOURCE_QUERY_ACTIONS_OPEN_CHAT:
          'dataplex.resource_query_actions.open_chat',
      RESOURCE_QUERY_ACTIONS_LOAD_IN_PANDAS_NOTEBOOK:
          'dataplex.resource_query_actions.load_in_pandas_notebook',
      RESOURCE_QUERY_ACTIONS_LOAD_IN_SPARK_NOTEBOOK:
          'dataplex.resource_query_actions.load_in_spark_notebook',
      RESOURCE_DATA_PREVIEW_DRY_RUN: 'dataplex.resourceDataPreview.dryRun'
    },
    CatalogCommand: {
      EXPLORER_REFRESH: 'google.datacloud.dataplex.explorer.refresh',
      OPEN_CATALOG_DETAILS: 'google.datacloud.dataplex.openCatalogDetails',
      FIND_IN_ALLOYDB: 'google.datacloud.dataplex.findInAlloyDb',
      FIND_IN_ALLOYDB_CLUSTER: 'google.datacloud.dataplex.findInAlloyDbCluster',
      FIND_IN_ALLOYDB_DATABASE:
          'google.datacloud.dataplex.findInAlloyDbDatabase',
      FIND_IN_ALLOYDB_SCHEMA: 'google.datacloud.dataplex.findInAlloyDbSchema',
      FIND_IN_CLOUDSQL: 'google.datacloud.dataplex.findInCloudSql',
      FIND_IN_CLOUDSQL_INSTANCE:
          'google.datacloud.dataplex.findInCloudSqlInstance',
      FIND_IN_CLOUDSQL_DATABASE:
          'google.datacloud.dataplex.findInCloudSqlDatabase',
      FIND_IN_CLOUDSQL_SCHEMA: 'google.datacloud.dataplex.findInCloudSqlSchema',
      FIND_IN_PROJECT: 'google.datacloud.dataplex.findInProject',
      FIND_IN_BIGLAKE: 'google.datacloud.dataplex.findInBigLake',
      FIND_IN_BIGLAKE_CATALOG: 'google.datacloud.dataplex.findInBigLakeCatalog',
      FIND_IN_BIGLAKE_NAMESPACE:
          'google.datacloud.dataplex.findInBigLakeNamespace',
      FIND_IN_BIGQUERY: 'google.datacloud.dataplex.findInBigQuery',
      FIND_IN_BIGQUERY_DATASET:
          'google.datacloud.dataplex.findInBigQueryDataset',
      FIND_IN_SPANNER: 'google.datacloud.dataplex.findInSpanner',
      FIND_IN_SPANNER_INSTANCE:
          'google.datacloud.dataplex.findInSpannerInstance',
      FIND_IN_SPANNER_DATABASE:
          'google.datacloud.dataplex.findInSpannerDatabase',
      QUERY_RESOURCE_WITH_BIGQUERY:
          'google.datacloud.dataplex.queryResourceWithBigQuery',
      QUERY_RESOURCE_WITH_SPARK:
          'google.datacloud.dataplex.queryResourceWithSpark',
      INTERNAL_TREE_LOAD_MORE:
          'google.datacloud.dataplex.internal.tree.loadMore',
      UNIVERSAL_SEARCH: 'google.datacloud.dataplex.universalSearch',
      SEMANTIC_SEARCH: 'google.datacloud.dataplex.semanticSearch',
      REFRESH_UNIVERSAL_CATALOG:
          'google.datacloud.dataplex.refreshUniversalCatalog',
      REFRESH_UNIVERSAL_CATALOG_ALL:
          'google.datacloud.dataplex.refreshUniversalCatalogAll',
      COPY_RESOURCE_ID: 'google.datacloud.dataplex.copyResourceId',
      QUERY_RESOURCE: 'google.datacloud.dataplex.queryResource',
      QUERY_RESOURCE_WITH_BIGQUERY_DATAFRAMES_NOTEBOOK:
          'google.datacloud.dataplex.queryResourceWithBigQueryDataFramesNotebook',
      QUERY_RESOURCE_WITH_PANDAS_NOTEBOOK:
          'google.datacloud.dataplex.queryResourceWithPandasNotebook',
      QUERY_RESOURCE_WITH_SPARK_NOTEBOOK:
          'google.datacloud.dataplex.queryResourceWithSparkNotebook',
      INSERT_RESOURCE_AT_CURSOR:
          'google.datacloud.dataplex.insertResourceAtCursor',
      REVEAL_RESOURCE: 'google.datacloud.dataplex.resource.reveal',
      REVEAL_BY_PATH: 'google.datacloud.dataplex.resource.revealByPath',
      FOCUS_RESOURCE_IF_REVEALED:
          'google.datacloud.dataplex.resource.focusIfRevealed',
      TRY_REVEAL_RESOURCE: 'google.datacloud.dataplex.resource.tryReveal',
      QUERY_FIRESTORE_STANDARD_DISABLED:
          'google.datacloud.dataplex.queryFirestoreStandardDisabled'
    },
    BigQueryEvent: {
      EXPLORER_EXPAND: 'google.datacloud.bigquery.explorer.expand',
      FETCH_JOBS: 'google.datacloud.bigquery.explorer.fetchJobs',
      FETCH_DATA_TRANSFERS:
          'google.datacloud.bigquery.explorer.fetchDataTransfers',
      FETCH_SAVED_QUERIES:
          'google.datacloud.bigquery.explorer.fetchSavedQueries',
      CACHE_UPDATE: 'google.datacloud.bigquery.explorer.cacheUpdate',
      JOB_DETAILS_IMPRESSION:
          'google.datacloud.bigquery.job.details.impression',
      JOB_DETAILS_TAB_CLICK: 'google.datacloud.bigquery.job.details.tabClick',
      DATA_TRANSFER_DETAILS_IMPRESSION:
          'google.datacloud.bigquery.dataTransfer.details.impression',
      DATA_TRANSFER_DETAILS_FETCH_RUNS:
          'google.datacloud.bigquery.dataTransfer.details.fetchRuns',
      DATA_TRANSFER_DETAILS_FETCH_CONFIG:
          'google.datacloud.bigquery.dataTransfer.details.fetchConfig',
      DATA_TRANSFER_DETAILS_TAB_CLICK:
          'google.datacloud.bigquery.dataTransfer.details.tabClick',
      JOB_OPEN_DETAILS: 'google.datacloud.bigquery.job.openDetails',
      DATA_TRANSFER_OPEN_DETAILS:
          'google.datacloud.bigquery.dataTransfer.openDetails',
      QUERY_SPARKLINE_CALCULATE:
          'google.datacloud.bigquery.query.sparkline.calculate',
      QUERY_RESULTS_PAGE_LOAD:
          'google.datacloud.bigquery.query.results.page.load',
      NOTEBOOK_LIST_SAMPLES: 'notebooks.bigquery.list-samples'
    },
    BigQueryCommand: {
      EXPLORER_REFRESH: 'google.datacloud.bigquery.explorer.refresh',
      EXPLORER_REFRESH_JOBS: 'google.datacloud.bigquery.explorer.refreshJobs',
      EXPLORER_REFRESH_QUERIES:
          'google.datacloud.bigquery.explorer.refreshQueries',
      EXPLORER_REFRESH_DATA_TRANSFERS:
          'google.datacloud.bigquery.explorer.refreshDataTransfers',
      TABLE_OPEN: 'google.datacloud.bigquery.table.open',
      QUERY_NEW: 'google.datacloud.bigquery.query.new',
      DATA_TRANSFER_ENABLE: 'google.datacloud.bigquery.datatransfer.enable',
      DATA_TRANSFER_DISABLE: 'google.datacloud.bigquery.datatransfer.disable',
      OPEN_TABLE: 'google.datacloud.bigquery.openTable',
      NOTEBOOK: 'google.datacloud.bigquery.notebook',
      NOTEBOOK_NEW: 'google.datacloud.bigquery.notebook.new',
      START_WITH_TEMPLATE: 'google.datacloud.bigquery.startWithTemplate',
      INTERNAL_TREE_LOAD_MORE:
          'google.datacloud.bigquery.internal.tree.loadMore',
      OPEN_SAVED_QUERY: 'google.datacloud.openSavedQuery',
      OPEN_JOB_DETAILS: 'google.datacloud.openJobDetails',
      OPEN_DATA_TRANSFER_DETAILS: 'google.datacloud.openDataTransferDetails',
      REFRESH_EXPLORER: 'google.datacloud.bigquery.refreshExplorer',
      REFRESH_JOBS: 'google.datacloud.bigquery.refreshJobs',
      REFRESH_QUERIES: 'google.datacloud.bigquery.refreshQueries',
      REFRESH_DATASETS: 'google.datacloud.bigquery.refreshDatasets',
      REFRESH_DATA_TRANSFERS: 'google.datacloud.bigquery.refreshDataTransfers',
      RENAME_SAVED_QUERY: 'google.datacloud.bigquery.savedquery.rename',
      DOWNLOAD_SAVED_QUERY: 'google.datacloud.bigquery.savedquery.download',
      DELETE_SAVED_QUERY: 'google.datacloud.bigquery.savedquery.delete'
    },
    OrchestrationPipelineEvent: {
      INITIALIZATION_IMPRESSION:
          'google.datacloud.orchestrationPipeline.initialization.impression',
      INITIALIZATION_SUBMIT:
          'google.datacloud.orchestrationPipeline.initialization.submit',
      DEPLOYMENT_CONFIGURATION_IMPRESSION:
          'google.datacloud.orchestrationPipeline.deploymentConfiguration.impression',
      DEPLOYMENT_CONFIGURATION_ADD_ENVIRONMENT:
          'google.datacloud.orchestrationPipeline.deploymentConfiguration.addEnvironment',
      DEPLOYMENT_CONFIGURATION_SAVE:
          'google.datacloud.orchestrationPipeline.deploymentConfiguration.save',
      PIPELINE_TRIGGER:
          'google.datacloud.orchestrationPipeline.pipeline.trigger',
      PIPELINE_INIT: 'google.datacloud.orchestrationPipeline.pipeline.init',
      PIPELINE_DEPLOY: 'google.datacloud.orchestrationPipeline.pipeline.deploy',
      PIPELINE_DELETE: 'google.datacloud.orchestrationPipeline.pipeline.delete',
      PIPELINE_SCHEDULE:
          'google.datacloud.orchestrationPipeline.pipeline.schedule',
      PIPELINE_DEPLOY_AND_RUN:
          'google.datacloud.orchestrationPipeline.pipeline.deployAndRun',
      VIEW_SOURCE_CODE:
          'google.datacloud.orchestrationPipeline.pipeline.viewSourceCode',
      REMOVE_PIPELINE: 'google.datacloud.orchestrationPipeline.pipeline.remove',
      SAVE_PIPELINE_YAML:
          'google.datacloud.orchestrationPipeline.pipeline.saveYaml',
      SWITCH_PIPELINE: 'google.datacloud.orchestrationPipeline.pipeline.switch',
      LIST_RUNS: 'google.datacloud.orchestrationPipeline.runs.list',
      PAUSE: 'google.datacloud.orchestrationPipeline.pipeline.pause',
      UNPAUSE: 'google.datacloud.orchestrationPipeline.pipeline.unpause',
      TROUBLESHOOT_PIPELINE_RUN:
          'google.datacloud.orchestrationPipeline.run.troubleshoot',
      LIST_PIPELINES: 'google.datacloud.orchestrationPipeline.pipelines.list',
      PIPELINE_MANAGEMENT_IMPRESSION:
          'google.datacloud.orchestrationPipeline.management.impression',
      SAVE_TASK_CONFIGURATION:
          'google.datacloud.orchestrationPipeline.task.saveConfiguration',
      ADD_TASK: 'google.datacloud.orchestrationPipeline.task.add',
      DELETE_TASK: 'google.datacloud.orchestrationPipeline.task.delete',
      DETAILS_PAGE_IMPRESSION:
          'google.datacloud.orchestrationPipeline.detailsPage.impression',
      DAG_VIEW_IMPRESSION:
          'google.datacloud.orchestrationPipeline.dagView.impression',
      TASK_CONFIGURATION_IMPRESSION:
          'google.datacloud.orchestrationPipeline.taskConfiguration.impression',
      RUNS_HISTORY_IMPRESSION:
          'google.datacloud.orchestrationPipeline.runsHistory.impression',
      PREREQUISITE_NOTIFICATION:
          'google.datacloud.orchestrationPipeline.prerequisite.notification',
      PREREQUISITE_ACTION:
          'google.datacloud.orchestrationPipeline.prerequisite.action'
    },
    OrchestrationPipelineCommand: {
      MANAGEMENT:
          'google.datacloud.bigquery.orchestrationPipeline.pipelineManagement',
      SHOW_DAG: 'google.datacloud.bigquery.orchestrationPipeline.showDag',
      INIT: 'google.datacloud.orchestrationPipeline.init',
      ADD_TASK: 'google.datacloud.bigquery.orchestrationPipeline.addTask',
      DELETE_TASK: 'google.datacloud.bigquery.orchestrationPipeline.deleteTask',
      SAVE_TASK_CONFIGURATION:
          'google.datacloud.bigquery.orchestrationPipeline.saveTaskConfiguration',
      SAVE_TRIGGER_CONFIGURATION:
          'google.datacloud.bigquery.orchestrationPipeline.saveTriggerConfiguration',
      SAVE_PIPELINE_SETTINGS:
          'google.datacloud.bigquery.orchestrationPipeline.savePipelineSettings',
      SHOW_DBT_COMPILED_GRAPH:
          'google.datacloud.bigquery.orchestrationPipeline.showDbtCompiledGraph',
      LEARN_MORE: 'google.datacloud.bigquery.orchestrationPipeline.learnMore',
      DETAILS_FULLY_QUALIFIED:
          'google.datacloud.bigquery.orchestrationPipeline.details.fullyQualified',
      DEPLOY_CONFIGURATION:
          'google.datacloud.bigquery.orchestrationPipeline.deployConfiguration',
      VIEW_COMPOSER_RUNS_HISTORY:
          'google.datacloud.bigquery.orchestrationPipeline.viewComposerRunsHistory',
      REFRESH_EXPLORER: 'google.datacloud.pipelines.refreshExplorer',
      CREATE_NEW: 'google.datacloud.bigquery.orchestrationPipeline.createNew'
    },
    NotebookSchedulingEvent:
        {JOB_SCHEDULE: 'google.datacloud.orchestration.job.schedule'},
    NotebookSchedulingCommand: {
      CREATE_SCHEDULED_JOB:
          'google.datacloud.bigquery.notebooks.createScheduledJob'
    },
    DataformEvent: {
      COMPILED_QUERY_IMPRESSION:
          'google.datacloud.bigquery.dataform.compiledQuery.impression',
      RUNS_HISTORY_IMPRESSION:
          'google.datacloud.bigquery.dataform.runsHistory.impression',
      GRAPH_RENDER: 'google.datacloud.bigquery.dataform.graph.render',
      GRAPH_REFRESH: 'google.datacloud.bigquery.dataform.graph.refresh'
    },
    DataformCommand: {
      INIT_PROJECT: 'google.datacloud.bigquery.dataform.initProject',
      COMPILE_PROJECT: 'google.datacloud.bigquery.dataform.compileProject',
      RUN_ACTIONS: 'google.datacloud.bigquery.dataform.runActions',
      RUN_TAGS: 'google.datacloud.bigquery.dataform.runTags',
      RUN: 'google.datacloud.bigquery.dataform.run',
      SHOW_COMPILED_GRAPH:
          'google.datacloud.bigquery.dataform.showCompiledGraph'
    },
    SqlEditorEvent: {
      QUERY_SETTINGS_UPDATE: 'google.datacloud.sqleditor.querySettings.update',
      DATABASE_AUTO_REVEAL: 'google.datacloud.sqleditor.database.autoReveal',
      QUERY_SUCCESS: 'google.datacloud.sqleditor.query.success',
      QUERY_FAILURE: 'google.datacloud.sqleditor.query.failure',
      RESULTS_PAGE: 'google.datacloud.sqleditor.results.page',
      RESULTS_PAGE_SIZE: 'google.datacloud.sqleditor.results.page-size',
      SETTINGS_SERVICE_SELECT:
          'google.datacloud.sqleditor.settings.service.select',
      SETTINGS_ENABLE_DATA_API:
          'google.datacloud.sqleditor.settings.dataApi.enable',
      SETTINGS_ENABLE_IAM_AUTH:
          'google.datacloud.sqleditor.settings.iamAuth.enable',
      SETTINGS_LOAD_RESOURCES:
          'google.datacloud.sqleditor.settings.resource.load',
      SETTINGS_LIST_PROJECTS:
          'google.datacloud.sqleditor.settings.project.list',
      JOB_HISTORY_QUERY_OPEN:
          'google.datacloud.sqleditor.job_history.query.open',
      QUERY_SETTINGS_VALIDATE:
          'google.datacloud.sqleditor.querySettings.validate',
      COPY_RESULTS: 'google.datacloud.sqleditor.results.copy',
      DOWNLOAD_RESULTS: 'google.datacloud.sqleditor.results.download',
      SAVE_RESULTS_TO_TABLE: 'google.datacloud.sqleditor.results.saveToTable',
      RECENT_CONNECTION_SELECT:
          'google.datacloud.sqleditor.recentConnection.select',
      RECENT_CONNECTION_REMOVE:
          'google.datacloud.sqleditor.recentConnection.remove',
      RUN_QUERY_ERROR_ACTION_CLICK:
          'google.datacloud.sqleditor.runQuery.errorAction.click',
      AUTOCOMPLETE_CRAWL: 'google.datacloud.sqleditor.autocomplete.crawl'
    },
    SqlQueryRunOutcome: {
      NO_EDITOR: 'no_editor',
      ALREADY_RUNNING: 'already_running',
      EMPTY_QUERY: 'empty_query',
      BLOCKED: 'blocked',
      SUBMIT_FAILED: 'submit_failed',
      SUCCEEDED: 'succeeded',
      FAILED: 'failed',
      CANCELLED: 'cancelled'
    },
    SqlQueryRunSurface: {
      SQL_EDITOR: 'sql_editor',
      CATALOG_PREVIEW: 'catalog_preview',
      UNKNOWN: 'unknown'
    },
    RecentConnectionLocation: {
      QUERY_SETTINGS_PANEL: 'query_settings_panel',
      CONNECTION_WIZARD: 'connection_wizard'
    },
    QuerySettingsSource:
        {COMMAND: 'command', WEBVIEW: 'webview', EMBEDDED: 'embedded'},
    SqlEditorCommand: {
      RUN_QUERY: 'google.datacloud.sqleditor.runQuery',
      CANCEL_QUERY: 'google.datacloud.sqleditor.cancelQuery',
      QUERY_RUNNING: 'google.datacloud.sqleditor.queryRunning',
      OPEN_QUERY_SETTINGS: 'google.datacloud.openQuerySettings',
      OPEN_QUERY_SETTINGS_BIGQUERY:
          'google.datacloud.openQuerySettings.bigquery',
      OPEN_QUERY_SETTINGS_BIGTABLE:
          'google.datacloud.openQuerySettings.bigtable',
      OPEN_QUERY_SETTINGS_SPANNER: 'google.datacloud.openQuerySettings.spanner',
      OPEN_QUERY_SETTINGS_ALLOYDB: 'google.datacloud.openQuerySettings.alloydb',
      OPEN_QUERY_SETTINGS_CLOUDSQL:
          'google.datacloud.openQuerySettings.cloudsql',
      UPDATE_QUERY_SETTINGS: 'google.datacloud.sqleditor.updateQuerySettings',
      GET_RECENT_QUERY_SETTINGS:
          'google.datacloud.sqleditor.querySettings.recent.get',
      REMOVE_RECENT_QUERY_SETTING:
          'google.datacloud.sqleditor.querySettings.recent.remove',
      REVEAL_IN_EXPLORER: 'google.datacloud.sqleditor.database.reveal',
      REFRESH_AUTOCOMPLETE_SCHEMA:
          'google.datacloud.sqleditor.autocomplete.refresh'
    },
    SqlEditorWizardEvent: {
      START: 'google.datacloud.sqleditor.wizard.start',
      STEP: 'google.datacloud.sqleditor.wizard.step',
      COMPLETE: 'google.datacloud.sqleditor.wizard.complete',
      CANCEL: 'google.datacloud.sqleditor.wizard.cancel',
      REDIRECT: 'google.datacloud.sqleditor.wizard.redirect',
      STEP_LOAD: 'google.datacloud.sqleditor.wizard.stepLoad'
    },
    SqlEditorWizardEntryPoint: {
      DATABASES_NEW_QUERY: 'databases_new_query',
      DATABASES_NEW_SERVICE_QUERY: 'databases_new_service_query',
      DATABASES_OPEN_QUERY: 'databases_open_query',
      DATABASES_TREE: 'databases_tree',
      CATALOG_TREE: 'catalog_tree',
      CATALOG_DETAILS: 'catalog_details',
      CATALOG: 'catalog'
    },
    OpenQueryFromFileOutcome: {
      FILE_DIALOG_CANCEL: 'file_dialog_cancel',
      FILE_DIALOG_FAILED: 'file_dialog_failed',
      OPEN_DOCUMENT_FAILED: 'open_document_failed',
      OPENED_WITH_EXISTING_CONNECTION: 'opened_with_existing_connection',
      OPENED_AND_CONNECTED: 'opened_and_connected',
      OPENED_WITHOUT_CONNECTION: 'opened_without_connection',
      WIZARD_REDIRECT: 'wizard_redirect'
    },
    SqlQueryUserError: {
      NOT_LOGGED_IN: 'not_logged_in',
      NO_PROJECT_SELECTED: 'no_project_selected',
      NO_DATASOURCE_SELECTED: 'no_datasource_selected'
    },
    SparkEvent: {
      CLUSTER_DETAILS_OPEN: 'google.datacloud.spark.clusterDetails.open',
      DRAG_AND_DROP_DRAG: 'google.datacloud.spark.dragAndDrop.drag',
      DRAG_AND_DROP_DROP: 'google.datacloud.spark.dragAndDrop.drop',
      JOB_DETAILS_LOAD: 'google.datacloud.spark.jobDetails.load',
      JOB_DELETE: 'google.datacloud.spark.jobDetails.delete',
      JOB_DETAILS_OPEN: 'google.datacloud.spark.jobDetails.open',
      JOB_DETAILS_OPEN_ERROR: 'google.datacloud.spark.jobDetails.open.error',
      SESSION_TEMPLATE_DETAILS_LOAD:
          'google.datacloud.spark.sessionTemplateDetails.load',
      SESSION_TEMPLATE_LIST: 'google.datacloud.spark.sessionTemplate.list',
      TOGGLE_IN_CELL_MONITORING:
          'google.datacloud.spark.settings.toggleInCellMonitoring',
      SUBMIT_JOB_OPEN: 'google.datacloud.spark.submitJob.open',
      SUBMIT_JOB_OPEN_ERROR: 'google.datacloud.spark.submitJob.open.error',
      CLUSTER_CREATE: 'google.datacloud.spark.cluster.create',
      CLUSTER_REFRESH: 'spark.cluster.refresh',
      CLUSTER_PROFILE_OPEN: 'google.datacloud.spark.clusterProfile.open',
      CLUSTER_PROFILE_OPEN_ERROR:
          'google.datacloud.spark.clusterProfile.open.error',
      CLUSTER_STOP: 'spark.cluster.stop',
      CLUSTER_STOP_ERROR: 'spark.cluster.stop.error',
      CLUSTER_START: 'spark.cluster.start',
      CLUSTER_START_ERROR: 'spark.cluster.start.error',
      CLUSTER_RESTART: 'google.datacloud.spark.cluster.restart',
      CLUSTER_RESTART_ERROR: 'google.datacloud.spark.cluster.restart.error',
      CLUSTER_PROFILE_REFRESH: 'spark.clusterProfile.refresh',
      CLUSTER_PROFILE_GET_CLUSTER: 'spark.clusterProfile.getCluster',
      CLUSTER_PROFILE_VIEW_LOGS: 'spark.clusterProfile.viewLogs',
      CLUSTER_PROFILE_VIEW_CLOUD_BUCKET: 'spark.clusterProfile.viewCloudBucket',
      CLUSTER_PROFILE_VIEW_IMAGE_VERSION_DOCS:
          'spark.clusterProfile.viewImageVersionDocumentation',
      SESSION_OPEN: 'spark.session.open',
      SESSION_DELETE_CLICK: 'spark.session.delete.click',
      SESSION_DELETE_CONFIRM: 'spark.session.delete.confirm',
      SESSION_STOP: 'spark.session.stop',
      SESSION_REFRESH: 'spark.session.refresh'
    },
    DataprocEvent: {
      JUPYTER_SERVER_RESOLVE: 'google.datacloud.jupyter.server.resolve',
      JUPYTER_KERNEL_STATUS: 'google.datacloud.jupyter.kernel.status',
      JUPYTER_TOKEN_EXCHANGE: 'google.datacloud.jupyter.token.exchange',
      CLUSTER_PROFILE_STOP: 'google.datacloud.dataproc.clusterProfile.stop',
      CLUSTER_PROFILE_START: 'google.datacloud.dataproc.clusterProfile.start',
      CLUSTER_PROFILE_DELETE: 'google.datacloud.dataproc.clusterProfile.delete',
      CLUSTER_DETAILS_IMPRESSION: 'dataproc.clusterDetails.impression'
    },
    DataprocCommand: {
      CREATE_SERVERLESS_NOTEBOOK:
          'google.datacloud.spark.serverless.newNotebook',
      CREATE_SERVERLESS_QUERY: 'google.datacloud.spark.serverless.newQuery',
      CREATE_SERVERLESS_RUNTIME:
          'google.datacloud.dataproc.serverless.runtimes.create',
      FIND_CLUSTER: 'google.datacloud.spark.clusters.findCluster',
      LIST_CLUSTERS: 'google.datacloud.spark.clusters.listClusters',
      LIST_CLUSTERS_MENU: 'google.datacloud.spark.clusters.listClusters.menu',
      LIST_SERVERLESS_RUNTIMES:
          'google.datacloud.spark.serverless.listRuntimes',
      LIST_SERVERLESS_RUNTIMES_MENU:
          'google.datacloud.spark.serverless.listRuntimes.menu',
      LOAD_MORE_CLUSTERS: 'google.datacloud.spark.clusters.loadMore',
      LOAD_MORE_SERVERLESS_RUNTIMES:
          'google.datacloud.spark.serverless.loadMore',
      OPEN_JOB_DETAILS: 'google.datacloud.spark.job.details',
      OPEN_SESSION_DETAILS: 'google.datacloud.spark.session.details',
      REFRESH_CLUSTERS: 'google.datacloud.dataproc.refreshClusters',
      REFRESH_SERVERLESS_RUNTIMES:
          'google.datacloud.dataproc.refreshServerless',
      REFRESH_SPARK_RESOURCE_TREE:
          'google.datacloud.dataproc.refreshSparkResourceTree',
      SPARK_CLUSTER_JOBS: 'google.datacloud.spark.cluster.jobs',
      SPARK_CLUSTER_PROFILE: 'google.datacloud.spark.cluster.profile',
      SPARK_CLUSTER_RESTART: 'google.datacloud.spark.cluster.restart',
      SPARK_CLUSTER_SPARK_UI: 'google.datacloud.spark.cluster.sparkUi',
      SPARK_CLUSTER_START: 'google.datacloud.spark.cluster.start',
      SPARK_CLUSTER_STATUS_PREFIX: 'google.datacloud.spark.cluster.status.',
      SPARK_CLUSTER_STOP: 'google.datacloud.spark.cluster.stop',
      SPARK_CLUSTER_SUBMIT_JOB: 'google.datacloud.spark.cluster.submitJob',
      SPARK_NEW_NOTEBOOK: 'google.datacloud.spark.newNotebook',
      SPARK_NEW_QUERY: 'google.datacloud.spark.newQuery',
      SPARK_SERVERLESS_FIND_RUNTIMES:
          'google.datacloud.spark.serverless.findRuntimes',
      SPARK_SERVERLESS_INTERACTIVE_SESSIONS:
          'google.datacloud.spark.serverless.interactiveSessions',
      SPARK_SERVERLESS_PROFILE: 'google.datacloud.spark.serverless.profile',
      SPARK_SESSION_STATUS_PREFIX: 'google.datacloud.spark.session.status.',
      SUBMIT_JOB_FROM_PALETTE:
          'google.datacloud.spark.cluster.submitJobFromPalette'
    },
    MlflowCommand: {OPEN_MLFLOW_UI: 'google.datacloud.mlflow.ui.open'},
    DataflowCommand: {LIST_JOBS: 'google.datacloud.dataflow.jobs.list'},
    DataflowEvent: {
      JOBS_REFRESH: 'google.datacloud.dataflow.jobs.refresh',
      JOBS_OPEN: 'google.datacloud.dataflow.jobs.open',
      JOBS_FILTER_APPLY: 'google.datacloud.dataflow.jobs.filter.apply',
      JOBS_FILTER_CLEAR: 'google.datacloud.dataflow.jobs.filter.clear'
    },
    SettingsCommands: {
      OPEN_SETTINGS: 'google.datacloud.settings',
      OPEN_SKILLS: 'google.datacloud.agent.skills.view',
      REFRESH_TREE: 'google.datacloud.settings.refreshTree',
      PIN_SETTINGS: 'google.datacloud.pinSettings',
      UNPIN_SETTINGS: 'google.datacloud.unpinSettings',
      OPEN_SCHEDULER_SETTINGS: 'google.datacloud.settings.scheduler.open',
      OPEN_EXPERIMENTS: 'google.datacloud.settings.experiments.open',
      OPEN_PROJECT_STATUS_BAR: 'google.datacloud.settings.projectStatusBar.open'
    },
    SettingsEvent: {SAVE: 'google.datacloud.settings.save'},
    McpEvent: {
      TOOL_EXECUTE: 'google.datacloud.mcp.tool.execute',
      TOOL_INVOKE: 'google.datacloud.mcp.tool.invoke',
      NOTEBOOKS_SERVER_START: 'google.datacloud.mcp.notebooks.server.start',
      NOTEBOOKS_SERVER_STOP: 'google.datacloud.mcp.notebooks.server.stop',
      DATA_AGENT_KIT_SERVER_START:
          'google.datacloud.data_agent_kit_mcp.server.start',
      DATA_AGENT_KIT_SERVER_STOP:
          'google.datacloud.data_agent_kit_mcp.server.stop',
      CONFIG_EXECUTE_CELL_TOGGLE:
          'google.datacloud.mcp.config.executeCell.toggle',
      CLI_AGENTS_TOGGLE: 'google.datacloud.mcp.cliAgents.toggle',
      CLI_AGENT_SELECT: 'google.datacloud.mcp.cliAgent.select',
      CLI_AGENT_COPY: 'google.datacloud.mcp.cliAgent.copy',
      CLI_AGENT_RUN: 'google.datacloud.mcp.cliAgent.run',
      CONFIG_OPEN: 'google.datacloud.mcp.config.open',
      CONFIG_SWITCH_VIEW: 'google.datacloud.mcp.config.switchView',
      SPANNER_READER_ERROR:
          'google.datacloud.data_agent_kit_mcp.spannerReaderError',
      ALLOYDB_READER_ERROR:
          'google.datacloud.data_agent_kit_mcp.alloydbReaderError',
      CLOUDSQL_READER_ERROR:
          'google.datacloud.data_agent_kit_mcp.cloudsqlReaderError'
    },
    McpCommand: {
      CONFIGURE_SERVERS: 'google.datacloud.mcp.servers.configure',
      CONFIGURE_SERVERS_FOR_SERVICES:
          'google.datacloud.mcp.servers.configureForServices',
      LIST_SERVERS: 'google.datacloud.mcp.servers.list',
      GET_CONFIG_PATH: 'google.datacloud.mcp.config.path.get',
      OPEN_CONFIG: 'google.datacloud.openMcpConfig'
    },
    DataAgentInterfaceCommand: {
      INSTALL_TOOLBOX_AS_MCP_SERVER:
          'google.datacloud.dataagentinterface.installToolboxAsMcpServer'
    },
    BigLakeIcebergEvent: {
      CATALOG_NAME_MISSING:
          'google.datacloud.biglakeiceberg.catalog.name.missing'
    },
    BigQueryGraphEvent: {
      GRAPH_RENDER: 'google.datacloud.bigquery.graph.render',
      GRAPH_SCHEMA_RENDER: 'google.datacloud.bigquery.graph.schema.render',
      GRAPH_DETAILS_RENDER: 'google.datacloud.bigquery.graph.details.render',
      GRAPH_CODE_RENDER: 'google.datacloud.bigquery.graph.code.render',
      FETCH_GRAPH_METADATA:
          'google.datacloud.bigquery.graph.fetchGraphMetadata',
      GRAPH_NODE_SELECT: 'google.datacloud.bigquery.graph.node.select',
      GRAPH_EDGE_SELECT: 'google.datacloud.bigquery.graph.edge.select',
      GRAPH_LABEL_SELECT: 'google.datacloud.bigquery.graph.label.select',
      GRAPH_ZOOM: 'google.datacloud.bigquery.graph.zoom'
    },
    DatabasesCommand: {
      QUERY_CREATE: 'google.datacloud.databases.query.create',
      QUERY_OPEN: 'google.datacloud.databases.query.open',
      QUERY_BIGTABLE_CREATE: 'google.datacloud.databases.query.bigtable.create',
      QUERY_SPANNER_CREATE: 'google.datacloud.databases.query.spanner.create',
      QUERY_ALLOYDB_CREATE: 'google.datacloud.databases.query.alloydb.create',
      QUERY_CLOUDSQL_CREATE: 'google.datacloud.databases.query.cloudsql.create',
      QUERY_FIRESTORE_CREATE:
          'google.datacloud.databases.query.firestore.create',
      START_GUIDED_TOUR: 'google.datacloud.databases.startGuidedTour',
      INTERNAL_TREE_LOAD_MORE:
          'google.datacloud.databases.internal.tree.loadMore',
      INTERNAL_TREE_REFRESH_ITEM:
          'google.datacloud.databases.internal.tree.refreshItem',
      REFRESH_EXPLORER: 'google.datacloud.databases.refreshExplorer',
      FOCUS_RESOURCE_IF_REVEALED:
          'google.datacloud.databases.resource.focusIfRevealed',
      REVEAL_RESOURCE: 'google.datacloud.databases.resource.reveal'
    },
    CalloutTourEvent: {
      CALLOUT_TOUR_START: 'google.datacloud.calloutTour.start',
      CALLOUT_TOUR_STEP_VIEW: 'google.datacloud.calloutTour.stepView',
      CALLOUT_TOUR_COMPLETE: 'google.datacloud.calloutTour.complete',
      CALLOUT_TOUR_DISMISS: 'google.datacloud.calloutTour.dismiss'
    },
    DatabasesEvent: {
      EXPLORER_EXPAND: 'google.datacloud.databases.explorer.expand',
      EXPLORER_FETCH_DURATION:
          'google.datacloud.databases.explorer.fetchDuration'
    },
    SkillEvent: {
      SKILL_INVOKE: 'google.datacloud.skills.skill.invoke',
      INSTALL_SKILL: 'google.datacloud.skills.skill.install',
      UNINSTALL_SKILL: 'google.datacloud.skills.skill.uninstall',
      TOGGLE_SKILL: 'google.datacloud.skills.skill.toggle',
      UPDATE_CONFIG_INSTALL_LOCATION:
          'google.datacloud.skills.config.installLocation.update',
      UPDATE_CONFIG_AUTO_UPDATE:
          'google.datacloud.skills.config.autoUpdate.update',
      SKILL_EDIT_SAVE: 'google.datacloud.skills.edit.save',
      SKILL_FILESYSTEM_DELETE: 'google.datacloud.skills.filesystem.delete',
      INSTALL_HOOKS: 'google.datacloud.skills.hooks.install',
      UNINSTALL_HOOKS: 'google.datacloud.skills.hooks.uninstall',
      DAK_CONFIG_UPDATE: 'google.datacloud.skills.dakConfig.update',
      AGY_PLUGIN_INSTALL: 'google.datacloud.skills.agyPlugin.install'
    },
    AgyPluginInstallResult: {
      MARKETPLACE: 'marketplace',
      GITHUB: 'github',
      AGY_NOT_FOUND: 'agy_not_found',
      FAILED: 'failed'
    },
    SkillUiEvent: {
      VIEW_OPEN: 'google.datacloud.skills.ui.view.open',
      ITEM_CLICK: 'google.datacloud.skills.ui.item.click',
      FILE_CLICK: 'google.datacloud.skills.ui.file.click',
      EDITOR_OPEN: 'google.datacloud.skills.ui.editor.open',
      ACTION_TOGGLE: 'google.datacloud.skills.ui.action.toggle',
      CONFIG_AUTO_UPDATE:
          'google.datacloud.skills.ui.config.auto_update.update',
      CONFIG_LOCATION:
          'google.datacloud.skills.ui.config.install_location.update',
      ACTION_RETRY: 'google.datacloud.skills.ui.action.retry',
      ACTION_FIX: 'google.datacloud.skills.ui.action.fix',
      OUTCOME_FIX: 'google.datacloud.skills.ui.outcome.fix',
      ACTION_INSTALL: 'google.datacloud.skills.ui.action.install',
      ACTION_UNINSTALL: 'google.datacloud.skills.ui.action.uninstall'
    },
    SkillCommand: {
      INSTALL_GLOBAL: 'google.datacloud.agent.skills.installGlobal',
      INSTALL_WORKSPACE: 'google.datacloud.agent.skills.installWorkspace',
      UNINSTALL_GLOBAL: 'google.datacloud.agent.skills.uninstallGlobal',
      UNINSTALL_WORKSPACE: 'google.datacloud.agent.skills.uninstallWorkspace',
      SYNC_FOR_SELECTED_SERVICES:
          'google.datacloud.agent.skills.syncSelectedServices'
    },
    AgyPluginCommand: {
      INSTALL: 'google.datacloud.agent.agyPlugin.install',
      RESET: 'google.datacloud.agent.agyPlugin.reset'
    },
    CloudResourceManagerEvent: {
      PROJECTS_SEARCH: 'google.datacloud.cloudResourceManager.projects.search',
      PROJECTS_GET: 'google.datacloud.cloudResourceManager.projects.get',
      PROJECTS_TEST_IAM_PERMISSIONS:
          'google.datacloud.cloudResourceManager.projects.testIamPermissions'
    },
    CloudSqlEvent: {
      AUTH_CONNECT: 'google.datacloud.cloudsql.auth.connect',
      SECRET_CREATE: 'google.datacloud.cloudsql.secret.create'
    },
    GoogleApiEvent: {
      SHARED_QUOTA_FALLBACK_RETRY:
          'google.datacloud.googleapis.sharedQuotaFallbackRetry',
      SHARED_QUOTA_EXHAUSTED:
          'google.datacloud.googleapis.sharedQuotaExhausted',
      ERROR: 'google.datacloud.googleapis.error'
    },
    FeedbackCommand: {PROVIDE_FEEDBACK: 'google.datacloud.provideFeedback'},
    FeedbackEvent: {SUBMIT: 'google.datacloud.feedback.submit'},
    GcloudCommand: {
      SYNC_FROM_EXTENSION_TO_GCLOUD_CONFIG:
          'google.datacloud.gcloud.config.syncFromExtensionToGcloud',
      SYNC_FROM_GCLOUD_TO_EXTENSION_CONFIG:
          'google.datacloud.gcloud.config.syncFromGcloudToExtension'
    },
    GcloudEvent: {
      SYNC_FROM_GCLOUD: 'google.datacloud.gcloud.sync.fromGcloud',
      SYNC_FROM_EXTENSION: 'google.datacloud.gcloud.sync.fromExtension',
      SYNC_PROMPT_CLICKED:
          'google.datacloud.gcloud.prompt.extensionToGcloudRecommended.click',
      GCLOUD_INSTALL_CLICK: 'google.datacloud.gcloud.installGcloud.click'
    },
    AuthCommand: {
      SIGN_IN: 'google.datacloud.auth.signIn',
      SIGN_OUT: 'google.datacloud.auth.signOut',
      OPEN_STATUS_BAR: 'google.datacloud.auth.statusBar.open'
    },
    AuthEvent: {
      AUTH_SIGN_OUT_CLICK: 'google.datacloud.auth.signOut.quickPick.click',
      STATUS_BAR_UPDATE: 'google.datacloud.auth.statusBar.update'
    },
    DataCloudCommand: {
      REVEAL_RESOURCE: 'google.datacloud.revealResource',
      FOCUS_ITEM_IF_REVEALED: 'google.datacloud.explorer.item.focusIfRevealed',
      TRY_REVEAL_ITEM: 'google.datacloud.explorer.item.tryReveal',
      VIEW_CATALOG: 'google.datacloud.view.catalog',
      VIEW_GCS: 'google.datacloud.view.gcs',
      VIEW_BIGQUERY: 'google.datacloud.view.bigquery',
      VIEW_SPARK: 'google.datacloud.view.spark',
      VIEW_PIPELINES: 'google.datacloud.view.pipelines',
      VIEW_DATABASES: 'google.datacloud.view.databases',
      VIEW_MLFLOW: 'google.datacloud.view.mlflow'
    },
    ErrorHandlingCommand: {HANDLE_API_ERROR: 'google.datacloud.handleApiError'},
    ErrorHandlingEvent: {
      API_ENABLE: 'google.datacloud.errorhandling.api.enable',
      COPY_ADMIN_REQUEST:
          'google.datacloud.errorhandling.action.copy_admin_request'
    },
    ConversationalAnalyticsCommand: {
      CHAT: 'google.datacloud.conversationalAnalytics.chat',
      CHAT_TABLE: 'google.datacloud.conversationalAnalytics.chatTable',
      CHAT_DATASET: 'google.datacloud.conversationalAnalytics.chatDataset',
      CHAT_EDITOR: 'google.datacloud.conversationalAnalytics.chatEditor',
      RUN_DIAGNOSTICS: 'google.datacloud.conversationalAnalytics.runDiagnostics'
    }
  };
  var module$exports$third_party$javascript$typings$node$node$https =
      (typeof require === 'function' ? require : function() {
        return {}
      })('https');
  var module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client =
      {};
  function
  module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_LogResponse() {
  }
  module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
      .LogResponse =
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_LogResponse;
  module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
      .USE_FIRELOG = !0;
  const
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_KEY =
          'IHAzhUhTlGX1SSCNlaw_YNOhvhfYmv5vCySazIA'.split(''),
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_IDENTIFIER =
          [
            ...module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_KEY
          ].reverse()
              .join('');
  function
  module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_decodeLogResponse(
      a) {
    if (!(a.length < 1)) {
      if (module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
              .USE_FIRELOG)
        try {
          var b = a.toString('utf8'), c = JSON.parse(b);
          if (c && typeof c === 'object') {
            var d = c.nextRequestWaitMillis;
            if (d !== void 0) {
              let e = Number(d);
              if (!isNaN(e)) return {
                  nextRequestWaitMs: e
                }
            }
          }
        } catch {
        }
      if (a.readUInt8(0) === 8) {
        b = BigInt(0);
        d = !0;
        for (c = 1; d && c < a.length; c++)
          d = a.readUInt8(c), b |= BigInt(d & 127) << BigInt(7 * (c - 1)),
          d = (d & 128) !== 0;
        if (!d) return {
            nextRequestWaitMs: Number(b)
          }
      }
    }
  }
  module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
      .decodeLogResponse =
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_decodeLogResponse;
  function
  module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_fixBuf(
      a) {
    return module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
               .USE_FIRELOG ?
        a :
        [a]
  }
  module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
      .fixBuf =
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_fixBuf;
  function
  module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_postMetricsToConcordServer(
      a, b) {
    return (new Promise((c, d) => {
             var e = {
               hostname: 'firebaselogging-pa.googleapis.com',
               path: `/v1/firelog/legacy/log?key=${
                   module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_IDENTIFIER}`,
               method: 'POST',
               headers: {
                 'Content-Length': Buffer.byteLength(a),
                 'Content-Type': 'application/json'
               }
             },
                 f = {
                   hostname: 'play.googleapis.com',
                   path: '/log',
                   method: 'POST',
                   headers: {'Content-Length': Buffer.byteLength(a)}
                 },
                 g = [];
             e = module$exports$third_party$javascript$typings$node$node$https
                     .request(
                         module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
                                 .USE_FIRELOG ?
                             e :
                             f,
                         h => {
                           h.on('data', l => g.push(l));
                           h.on('end', () => {c(Buffer.concat(g))})
                         });
             e.on('error', h => {
               b && b(h);
               d(h)
             });
             e.end(a)
           }))
        .then(c => {
          try {
            return module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_decodeLogResponse(
                       c) ||
            {}
          } catch {
            return {}
          }
        })
  }
  module$exports$third_party$cloudcode$vscode$common$packages$metrics$concord_client
      .postMetricsToConcordServer =
      module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_postMetricsToConcordServer;
  var module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants =
      {
        DataCloudMetadataKey: {
          GCLOUD_PROPERTY: 'gcloudProperty',
          VIEW_NAME: 'datacloudViewName',
          UNIVERSAL_SEARCH_TRIGGER_SOURCE: 'searchTriggerSource',
          UNIVERSAL_SEARCH_RESOURCE_TYPE: 'resourceType',
          UNIVERSAL_SEARCH_RESULT_RANK: 'resultRank',
          UNIVERSAL_SEARCH_HAS_SYSTEMS_FILTER: 'hasSystemsFilter',
          UNIVERSAL_SEARCH_HAS_PROJECTS_FILTER: 'hasProjectsFilter',
          UNIVERSAL_SEARCH_HAS_LOCATION_FILTER: 'hasLocationFilter',
          UNIVERSAL_SEARCH_HAS_TYPE_FILTER: 'hasTypeFilter',
          UNIVERSAL_SEARCH_HAS_SUBTYPE_FILTER: 'hasSubTypeFilter',
          UNIVERSAL_SEARCH_QUERY_WORD_COUNT: 'searchQueryWordCount',
          UNIVERSAL_SEARCH_QUERY_OPERATOR_EQUAL_COUNT:
              'searchQueryOperatorEqualCount',
          UNIVERSAL_SEARCH_QUERY_OPERATOR_INCLUDE_COUNT:
              'searchQueryOperatorIncludeCount',
          UNIVERSAL_SEARCH_FREE_TEXT_SEARCH_WORD_COUNT:
              'freeTextSearchWordCount',
          UNIVERSAL_SEARCH_ERROR_CODE: 'errorCode',
          UNIVERSAL_SEARCH_RESULT_COUNT: 'resultCount',
          UNIVERSAL_SEARCH_ENTRY_POINT: 'searchEntryPoint',
          UNIVERSAL_SEARCH_FILTER_TYPE_ADDED: 'filterTypeAdded',
          UNIVERSAL_SEARCH_FILTER_TYPE_REMOVED: 'filterTypeRemoved',
          SKILL_ID: 'skill_id',
          INSTALL_LOCATION: 'install_location',
          ENABLED: 'enabled',
          REASON: 'reason',
          WEBVIEW_ERROR: 'webviewError',
          FILE_NAME: 'file_name',
          OUTCOME: 'outcome',
          AGENT_ID: 'agent_id',
          ERROR_TYPE: 'error_type',
          STATUS: 'status',
          TYPE: 'type',
          PREVIOUS_STATUS: 'previousStatus',
          ACTION: 'action',
          MCP_SERVER_NAME: 'mcpServerName',
          MCP_TOOL_NAME: 'mcpToolName',
          MCP_ARGUMENT_KEYS: 'mcpArgumentKeys',
          MCP_ARGUMENTS_SUMMARY: 'mcpArgumentsSummary',
          SAVED_SETTING: 'savedSetting',
          RESOURCE_ID: 'resource_id',
          RESOURCE_TYPE: 'resource_type',
          RESOURCE_COUNT: 'resource_count',
          RESOURCE_TYPES: 'resource_types',
          DB_TYPE: 'dbType',
          SCHEMA_FIELD_COUNT: 'schemaFieldCount',
          IS_DRY_RUN: 'isDryRun',
          NOTEBOOK_TYPE: 'notebook_type',
          NOTEBOOK_KERNEL_TYPE: 'notebook_kernel_type',
          NOTEBOOK_IS_SAMPLE: 'notebook_is_sample',
          NOTEBOOK_SAMPLE_URL: 'notebook_sample_url',
          AUTH_STATUS_BAR_HAS_WARNINGS: 'authStatusBarHasWarnings',
          AUTH_STATUS_BAR_ACCOUNT_MISMATCH: 'authStatusBarAccountMismatch',
          CORRELATION_ID: 'correlation_id',
          EXECUTE_CELL_TOOL_FOR_NOTEBOOK_MCP: 'executeCellToolForNotebookMcp',
          EXECUTE_CELL_TOOL_CONSENT: 'executeCellToolConsent',
          HAS_NODE_IN_SYSTEM_PATH: 'has_node_in_system_path',
          AGENT_RUNTIME: 'agent_runtime',
          HOOK_INSTALL_SOURCE: 'hook_install_source',
          GRAPH_NODE_COUNT: 'graphNodeCount',
          GRAPH_EDGE_COUNT: 'graphEdgeCount',
          UI_LOCATION: 'ui_location',
          ZOOM_ACTION: 'zoom_action',
          ZOOMED_TO: 'zoomed_to',
          AUTH_METHOD: 'authMethod',
          SELECTED_SERVICES: 'selectedServices',
          SERVICES_COUNT: 'servicesCount',
          APIS_TO_ENABLE: 'apisToEnable',
          ENABLED_APIS: 'enabledApis',
          DISABLED_APIS: 'disabledApis',
          MISSING_PERMISSIONS: 'missingPermissions',
          MISSING_PERMISSIONS_COUNT: 'missingPermissionsCount',
          SERVICES_WITH_MISSING_PERMISSIONS: 'servicesWithMissingPermissions',
          STEP_INDEX: 'stepIndex',
          STEP_COUNT: 'stepCount'
        },
        DataCloudMetadataValue: {
          NOTEBOOK_TYPE_BIGQUERY: 'BigQuery',
          NOTEBOOK_TYPE_SPARK: 'Spark',
          NOTEBOOK_KERNEL_TYPE_LOCAL: 'Local',
          NOTEBOOK_KERNEL_TYPE_REMOTE: 'Remote'
        }
      };
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook =
      {};
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
      .POST_METRICS_FN =
      new module$exports$cloud$developer_experience$datacloud_vscode$common$exthost$inject$types
          .InjectionKey(
              'cloud/developer_experience/datacloud_vscode/agents/hooks/telemetry_hook.ts:post-metrics-fn');
  module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
      .TelemetryHook = class {
    constructor() {
      this.isLocalTelemetry =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .IS_LOCAL_TELEMETRY);
      this.postMetrics =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
                  .POST_METRICS_FN);
      this.fileSystem =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .FS_DEPS);
      this.identityResolver =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$user_identity
                  .UserIdentityResolver);
      this.projectResolver =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$project_resolver
                  .ProjectResolver);
      this.os =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .OS_DEPS);
      this.processEnv =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                  .PROCESS_ENV);
      this.skillParser =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$skill_parser
                  .SkillParser);
      this.mcpParser =
          module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$mcp_parser
                  .McpParser)
    }
    async executeTelemetry(a, b, c) {
      var d = $jscomp.asyncContextStart(), e = d();
      d = d(1);
      try {
        try {
          let k = JSON.parse(a), m = k;
          k.preToolHookArgs &&
                  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                      k.preToolHookArgs) ?
              m = k.preToolHookArgs :
              k.toolHookArgs &&
                  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$utils_isRecord(
                      k.toolHookArgs) &&
                  (m = k.toolHookArgs);
          if (!this.shouldSkipTelemetryAndLock(a)) {
            var f = this.skillParser.parseSkillInfo(m), g,
                h = (g = f) == null ? void 0 : g.isGooglePublisher,
                l = this.mcpParser.parseMcpInfo(m), p,
                q = !((p = l) == null || !p.isGoogleTool);
            if (h || q) {
              var r = this.identityResolver.resolveIdentity();
              if (r) {
                var t = Date.now(), u = this.compileEvent(r, t, {
                  skill: h ? f : void 0,
                  mcp: q ? l : void 0,
                  agentName: b,
                  installSource: c
                }),
                    v = this.wrapInFirelogEnvelope(u, t), n = JSON.stringify(v);
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                    `Compiling payload: ${n} (local: ${
                        this.isLocalTelemetry})`);
                this.isLocalTelemetry ? this.writeToLocalLog(n) :
                                        d(await e(this.postToConcord(n)))
              } else
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                    'No user identity or installation ID detected. Telemetry skipped.')
            } else
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                  'Not a verified Google skill or Google MCP tool invocation. Telemetry skipped.')
          }
        } catch (k) {
          d(),
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                  'Failed to compile telemetry payload', k)
        }
      } finally {
        e()
      }
    }
    compileEvent(a, b, c) {
      b = '';
      var d = [];
      c.skill ?
          (b = module$exports$cloud$developer_experience$datacloud_vscode$common$telemetry$constants
                   .SkillEvent.SKILL_INVOKE,
           d.push({
             key:
                 module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants
                     .DataCloudMetadataKey.SKILL_ID,
             value: c.skill.skillName
           })) :
          c.mcp &&
              (b = module$exports$cloud$developer_experience$datacloud_vscode$common$telemetry$constants
                       .McpEvent.TOOL_INVOKE,
               d.push(
                   {
                     key:
                         module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants
                             .DataCloudMetadataKey.MCP_TOOL_NAME,
                     value: c.mcp.toolName
                   },
                   {
                     key:
                         module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants
                             .DataCloudMetadataKey.MCP_SERVER_NAME,
                     value: c.mcp.serverName
                   }));
      c.agentName && d.push({
        key:
            module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants
                .DataCloudMetadataKey.AGENT_RUNTIME,
        value: c.agentName
      });
      c.installSource && d.push({
        key:
            module$exports$third_party$cloudcode$vscode$common$packages$metrics$datacloud$constants
                .DataCloudMetadataKey.HOOK_INSTALL_SOURCE,
        value: c.installSource
      });
      d.push({key: 'editor_name', value: this.getEditorName()});
      d.push(
          {
            key: 'ext_name',
            value:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
                    .EXT_NAME
          },
          {
            key: 'ext_version',
            value:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
                    .EXT_VERSION
          },
          {key: 'os_platform', value: this.processEnv.platform},
          {key: 'arch_platform', value: this.processEnv.arch},
          {key: 'os_release', value: this.os.release()});
      c = new Date(
          module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
              .BUILD_TIMESTAMP *
          1E3);
      c = module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
                  .BUILD_TIMESTAMP > 0 ?
          c.toISOString() :
          'UNKNOWN_BUILD_DATE';
      d.push(
          {
            key: 'change_list',
            value:
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$build_info
                    .BUILD_CHANGELIST
          },
          {key: 'built_on', value: c});
      c = !!this.processEnv.env.GOOGLE_CLOUD_WORKSTATIONS;
      var e = this.processEnv.env.EDITOR_IN_CLOUD_SHELL === 'true';
      d.push(
          {key: 'is_cloud_workstations', value: c.toString()},
          {key: 'is_cloud_shell', value: e.toString()});
      b = {
        console_type: 'CLOUDCODE_VSCODE',
        event_name: b,
        environment: this.isLocalTelemetry ? 'DEV' : 'PROD',
        event_metadata: d
      };
      a.email ? b.client_email = a.email : b.client_install_id = a.installId;
      (a = this.projectResolver.resolveProject()) && (b.project_id = a);
      return b
    }
    ensureTelemetryDir() {
      var a =
          module$exports$third_party$javascript$typings$node$node$path
              .join(this.os.tmpdir(), 'datacloud_telemetry');
      try {
        this.fileSystem.existsSync(a) ||
            this.fileSystem.mkdirSync(a, {recursive: !0})
      } catch (b) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            `Failed to create telemetry directory: ${b}`)
      }
      return a
    }
    shouldSkipTelemetryAndLock(a) {
      var b = this.ensureTelemetryDir();
      a = module$exports$third_party$javascript$typings$node$node$crypto
              .createHash('md5')
              .update(a)
              .digest('hex');
      b = module$exports$third_party$javascript$typings$node$node$path
              .join(b, `${a}.lock`);
      a = Date.now();
      if (this.fileSystem.existsSync(b)) try {
          let c = this.fileSystem.readFileSync(b, 'utf8').trim(), d = Number(c);
          if (!isNaN(d) && a - d < 5E3)
            return module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                       'Telemetry already executed recently for this payload. Skipping.'),
                   !0
        } catch (c) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              `Failed to read lock file: ${c}`)
        }
      try {
        this.fileSystem.writeFileSync(b, String(a), {encoding: 'utf8'})
      } catch (c) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            `Failed to write lock file: ${c}`)
      }
      return !1
    }
    wrapInFirelogEnvelope(a, b) {
      return {
        client_info: {
          client_type: 'DESKTOP',
          desktop_client_info: {os: this.processEnv.platform}
        },
            log_source_name: 'CONCORD', request_time_ms: b,
            log_event:
                [{event_time_ms: b, source_extension_json: JSON.stringify(a)}]
      }
    }
    writeToLocalLog(a) {
      module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
          '[LOCAL ONLY] Intercepted telemetry event. Writing to local log...');
      var b =
          module$exports$third_party$javascript$typings$node$node$path
              .join(this.ensureTelemetryDir(), 'local_log.json');
      try {
        this.fileSystem.appendFileSync(b, a + '\n', 'utf8')
      } catch (c) {
        module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
            'Failed to write local log', c)
      }
    }
    async postToConcord(a) {
      var b = $jscomp.asyncContextStart(), c = b();
      b = b(1);
      try {
        try {
          let d = b(await c(this.postMetrics(a)));
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              `Post completed. Next request wait: ${d.nextRequestWaitMs}ms`)
        } catch (d) {
          b(),
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                  'Post failed', d)
        }
      } finally {
        c()
      }
    }
    getEditorName() {
      var a = this.processEnv.env.DATA_CLOUD_CURR_IDE_NAME;
      return a ? a :
          this.processEnv.env.AI_AGENT === 'github_copilot_vscode_agent' ?
                 'visualstudiocode' :
          this.processEnv.env.ANTIGRAVITY_EDITOR_APP_ROOT ? 'antigravityide' :
          this.processEnv.env.CURSOR_VERSION              ? 'cursor' :
          this.processEnv.env.TERM_PROGRAM === 'kiro'     ? 'kiro' :
          this.processEnv.env.VSCODE_PID                  ? 'visualstudiocode' :
                                                            'cli'
    }
  };
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [
        {
          key:
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
                  .POST_METRICS_FN,
          factory: () =>
              module$contents$third_party$cloudcode$vscode$common$packages$metrics$concord_client_postMetricsToConcordServer
        },
        {
          key:
              module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
                  .TelemetryHook,
          factory: () =>
              new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
                  .TelemetryHook
        }
      ]);
  var module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner = {
    HookSpawner: class {
      constructor() {
        this.spawnFn =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .SPAWN_FN);
        this.processEnv =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .PROCESS_ENV);
        this.telemetryHook =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$telemetry_hook
                    .TelemetryHook);
        this.fsDeps =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers
                    .FS_DEPS);
        this.identityResolver =
            module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
                module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$user_identity
                    .UserIdentityResolver)
      }
      async spawnHook() {
        var a = $jscomp.asyncContextStart(), b = a();
        a = a(1);
        try {
          let d = this.processEnv.argv,
              e = module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner_getArg(
                  d, '--agent_name'),
              f = module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner_getArg(
                  d, '--install_source');
          if (this.identityResolver.isTelemetryEnabled()) {
            var c =
                module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner_getArg(
                    d, '--background');
            c !== void 0 ? a(await b(this.runBackground(c, e, f))) :
                           (this.runMain(d[1], e, f), this.writeAndExit(e))
          } else
            module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                'Telemetry is disabled by user configuration. Exiting early.'),
                this.writeAndExit(e)
        } finally {
          b()
        }
      }
      writeAndExit(a) {
        a = a === 'cursor' ? JSON.stringify({permission: 'allow'}) :
            a === 'copilot' || a === 'claude' || a === 'codex' ?
                             JSON.stringify({}) :
                             JSON.stringify({decision: 'allow'});
        this.processEnv.stdout.write(a);
        this.processEnv.exit(0)
      }
      async runBackground(a, b, c) {
        var d = $jscomp.asyncContextStart(), e = d();
        d = d(1);
        try {
          if (a) try {
              module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                  `Running in background child process (agent: ${b}, source: ${
                      c})...`),
                  d(await e(this.telemetryHook.executeTelemetry(a, b, c)))
            } catch (f) {
              d(),
                  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                      'Background execution error', f)
            }
          else
            module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                'Missing background payload argument.')
        } finally {
          e()
        }
      }
      runMain(a, b, c) {
        try {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Running in main hook process...');
          let d = this.fsDeps.readFileSync(0, 'utf8').trim();
          if (d) {
            module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                'Spawning detached background process...');
            a = [a, '--background', d];
            b && a.push('--agent_name', b);
            c && a.push('--install_source', c);
            let e = this.spawnFn(
                this.processEnv.execPath, a, {detached: !0, stdio: 'ignore'});
            e.unref();
            module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
                'Background process spawned and unreferenced.')
          }
        } catch (d) {
          module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$logging_debugLog(
              'Failed to spawn background process', d)
        }
      }
    }
  };
  function
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner_getArg(
      a, b) {
    b = a.indexOf(b);
    if (b !== -1 && b + 1 < a.length) return a[b + 1]
  }
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_addProviders(
      [{
        key:
            module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner
                .HookSpawner,
        factory: () =>
            new module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner
                .HookSpawner
      }]);
  module$contents$cloud$developer_experience$datacloud_vscode$agents$hooks$common_providers_setupCommonProviders(
      {isLocalTelemetry: !1});
  module$contents$cloud$developer_experience$datacloud_vscode$common$exthost$inject$internal_inject(
      module$exports$cloud$developer_experience$datacloud_vscode$agents$hooks$hook_spawner
          .HookSpawner)
      .spawnHook();
}
     .call(
         Object.assign(Object.create(globalThis), {
           'CLOSURE_NO_DEPS': true,
           'CLOSURE_UNCOMPILED_DEFINES': {'goog.SEAL_MODULE_EXPORTS': false}
         }),
         module.exports);

// # sourceMappingURL=telemetry_hook_bundle_prod.cjs.map
