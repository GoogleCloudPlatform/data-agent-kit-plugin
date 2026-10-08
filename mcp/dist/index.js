#!/usr/bin/env node
/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(async () => {
  const __isCjs = typeof require !== "undefined" && typeof module !== "undefined";
  const __path = __isCjs ? require("path") : await import("node:path");
  const __file = __isCjs ? __filename : __path.resolve(process.argv[1]);
  const __dir = __isCjs ? __dirname : __path.dirname(__file);
  const __req = __isCjs ? require : (await import("node:module")).createRequire(__file);
  const __mod = __isCjs ? module : { exports: {} };
  (function(require, __filename, __dirname, module, exports) {
!function ($$NODEJS_EXPORTS_OBJECT$$) {
const __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb)((mod = {exports: {}}).exports, mod), mod.exports;
};

var goog;
Object.defineProperty(this, 'goog', {
  get() { return goog; },
  set(v) { goog = v; },
});
/**
 * @license
 * Copyright The Closure Library Authors.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @fileoverview Bootstrap for the Google JS Library (Closure).
 *
 * Avoid including base.js more than once. This is strictly discouraged and not
 * supported. goog.require(...) won't work properly in that case.
 *
 * @suppress {deprecated} Users cannot remove deprecated uses here.
 * @provideGoog
 */


/**
 * @define {boolean} Overridden to true by the compiler.
 */
var COMPILED = false;


/**
 * Base namespace for the Closure library.  Checks to see goog is already
 * defined in the current scope before assigning to prevent clobbering if
 * base.js is loaded more than once.
 *
 * @const
 */
var goog = goog || {};

/**
 * Reference to the global object.
 * https://www.ecma-international.org/ecma-262/9.0/index.html#sec-global-object
 *
 * More info on this implementation here:
 * https://docs.google.com/document/d/1NAeW4Wk7I7FV0Y2tcUFvQdGMc89k2vdgSXInw8_nvCI/edit
 *
 * @const
 * @suppress {undefinedVars} self won't be referenced unless `this` is falsy.
 * @type {!Global}
 */
goog.global =
    // Check `this` first for backwards compatibility.
    // Valid unless running as an ES module or in a function wrapper called
    //   without setting `this` properly.
    // Note that base.js can't usefully be imported as an ES module, but it may
    // be compiled into bundles that are loadable as ES modules.
    this ||
    // https://developer.mozilla.org/en-US/docs/Web/API/Window/self
    // For in-page browser environments and workers.
    self;


/**
 * A hook for overriding the define values in uncompiled mode.
 *
 * In uncompiled mode, `CLOSURE_UNCOMPILED_DEFINES` may be defined before
 * loading base.js.  If a key is defined in `CLOSURE_UNCOMPILED_DEFINES`,
 * `goog.define` will use the value instead of the default value.  This
 * allows flags to be overwritten without compilation (this is normally
 * accomplished with the compiler's "define" flag).
 *
 * Example:
 * <pre>
 *   var CLOSURE_UNCOMPILED_DEFINES = {'goog.DEBUG': false};
 * </pre>
 *
 * @type {Object<string, (string|number|boolean)>|undefined}
 */
goog.global.CLOSURE_UNCOMPILED_DEFINES;


/**
 * A hook for overriding the define values in uncompiled or compiled mode,
 * like CLOSURE_UNCOMPILED_DEFINES but effective in compiled code.  In
 * uncompiled code CLOSURE_UNCOMPILED_DEFINES takes precedence.
 *
 * Also unlike CLOSURE_UNCOMPILED_DEFINES the values must be number, boolean or
 * string literals or the compiler will emit an error.
 *
 * While any @define value may be set, only those set with goog.define will be
 * effective for uncompiled code.
 *
 * Example:
 * <pre>
 *   var CLOSURE_DEFINES = {'goog.DEBUG': false} ;
 * </pre>
 *
 * Currently the Closure Compiler will only recognize very simple definitions of
 * this value when looking for values to apply to compiled code and ignore all
 * other references.  Specifically, it looks the value defined at the variable
 * declaration, as with the example above.
 *
 * TODO: Improve the recognized definitions.
 *
 * @type {!Object<string, (string|number|boolean)>|null|undefined}
 */
goog.global.CLOSURE_DEFINES;


/**
 * Builds an object structure for the provided namespace path, ensuring that
 * names that already exist are not overwritten. For example:
 * "a.b.c" -> a = {};a.b={};a.b.c={};
 * Used by goog.provide and goog.exportSymbol.
 * @param {string} name The name of the object that this file defines.
 * @param {*=} object The object to expose at the end of the path.
 * @param {boolean=} overwriteImplicit If object is set and a previous call
 *     implicitly constructed the namespace given by name, this parameter
 *     controls whether object should overwrite the implicitly constructed
 *     namespace or be merged into it. Defaults to false.
 * @param {?Object=} objectToExportTo The object to add the path to; if this
 *     field is not specified, its value defaults to `goog.global`.
 * @private
 */
goog.exportPath_ = function(name, object, overwriteImplicit, objectToExportTo) {
  var parts = name.split('.');
  var cur = objectToExportTo || goog.global;

  for (var part; parts.length && (part = parts.shift());) {
    if (!parts.length && object !== undefined) {
      if (!overwriteImplicit && goog.isObject(object) &&
          goog.isObject(cur[part])) {
        // Merge properties on object (the input parameter) with the existing
        // implicitly defined namespace, so as to not clobber previously
        // defined child namespaces.
        for (var prop in object) {
          if (object.hasOwnProperty(prop)) {
            cur[part][prop] = object[prop];
          }
        }
      } else {
        // Either there is no existing implicit namespace, or overwriteImplicit
        // is set to true, so directly assign object (the input parameter) to
        // the namespace.
        cur[part] = object;
      }
    } else if (cur[part] && cur[part] !== Object.prototype[part]) {
      cur = cur[part];
    } else {
      cur = cur[part] = {};
    }
  }
};

/**
 * Defines local copies for isolation of multiple chunk set. These values must
 * be set before closure base in order to have goog.define properly work.
 *
 * @suppress {checkVars}
 */
goog.CLOSURE_DEFINES = typeof CLOSURE_DEFINES !== 'undefined' ?
    CLOSURE_DEFINES :
    goog.global.CLOSURE_DEFINES;
/**
 * @suppress {checkVars}
 */
goog.CLOSURE_UNCOMPILED_DEFINES =
    typeof CLOSURE_UNCOMPILED_DEFINES !== 'undefined' ?
    CLOSURE_UNCOMPILED_DEFINES :
    goog.global.CLOSURE_UNCOMPILED_DEFINES;

/**
 * Defines a named value. In uncompiled mode, the value is retrieved from
 * CLOSURE_DEFINES or CLOSURE_UNCOMPILED_DEFINES if the object is defined and
 * has the property specified, and otherwise used the defined defaultValue.
 * When compiled the default can be overridden using the compiler options or the
 * value set in the CLOSURE_DEFINES object. Returns the defined value so that it
 * can be used safely in modules. Note that the value type MUST be either
 * boolean, number, or string.
 *
 * @suppress {checkVars|lintChecks}
 *
 * @param {string} name The distinguished name to provide.
 * @param {T} defaultValue
 * @return {T} The defined value.
 * @template T
 * @tsType (name: string, defaultValue: boolean): boolean
 * @tsType (name: string, defaultValue: number): number
 * @tsType (name: string, defaultValue: string): string
 */
goog.define = function(name, defaultValue) {
  var value = defaultValue;
  if (!COMPILED) {
    // Fallback to goog.global.CLOSURE_UNCOMPILED_DEFINES in the
    // case that the value is set after closure base. This keeps existing code
    // working.
    var uncompiledDefines = goog.CLOSURE_UNCOMPILED_DEFINES ?
        goog.CLOSURE_UNCOMPILED_DEFINES :
        goog.global.CLOSURE_UNCOMPILED_DEFINES;
    // Fallback to goog.global.CLOSURE_DEFINES in the case that the
    // value is set after closure base. This keeps existing code working.
    var defines = goog.CLOSURE_DEFINES ? goog.CLOSURE_DEFINES :
                                         goog.global.CLOSURE_DEFINES;
    if (uncompiledDefines &&
        // Anti DOM-clobbering runtime check (b/37736576).
        /** @type {?} */ (uncompiledDefines).nodeType === undefined &&
        Object.prototype.hasOwnProperty.call(uncompiledDefines, name)) {
      value = uncompiledDefines[name];
    } else if (
        defines &&
        // Anti DOM-clobbering runtime check (b/37736576).
        /** @type {?} */ (defines).nodeType === undefined &&
        Object.prototype.hasOwnProperty.call(defines, name)) {
      value = defines[name];
    }
  }
  return value;
};


/**
 * @define {number} Integer year indicating the set of browser features that are
 * guaranteed to be present.  This is defined to include exactly features that
 * work correctly on all "modern" browsers that are stable on January 1 of the
 * specified year.  For example,
 * ```js
 * if (goog.FEATURESET_YEAR >= 2019 || featureDetectionForAPI()) {
 *   // use APIs known to be available on all major stable browsers Jan 1, 2019
 * } else {
 *   // polyfill for older browsers
 * }
 * ```
 * This is intended to be the primary define for removing
 * unnecessary browser compatibility code (such as ponyfills and workarounds),
 * and should inform the default value for most other defines:
 * ```js
 * const ASSUME_NATIVE_PROMISE =
 *     goog.define('ASSUME_NATIVE_PROMISE', goog.FEATURESET_YEAR >= 2016);
 * ```
 *
 * The default assumption is that IE9 is the lowest supported browser, which was
 * first available Jan 1, 2012.
 *
 * When used in common code, the only allowed usage is to short-circuit feature
 * detection in order to statically eliminate unnecessary fallback code.
 * Changing the feature set year setting MUST NOT change any runtime behavior on
 * browsers where the feature is present.  In other words, NEVER use a
 * `FEATURESET_YEAR > X` check without a corresponding `|| runtimeFeatureDetection()`
 *
 * See go/bfsy for details.
 */
goog.FEATURESET_YEAR = goog.define('goog.FEATURESET_YEAR', 2012);


/**
 * @define {boolean} DEBUG is provided as a convenience so that debugging code
 * that should not be included in a production. It can be easily stripped
 * by specifying --define goog.DEBUG=false to the Closure Compiler aka
 * JSCompiler. For example, most toString() methods should be declared inside an
 * "if (goog.DEBUG)" conditional because they are generally used for debugging
 * purposes and it is difficult for the JSCompiler to statically determine
 * whether they are used.
 */
goog.DEBUG = goog.define('goog.DEBUG', true);


/**
 * @define {string} LOCALE defines the locale being used for compilation. It is
 * used to select locale specific data to be compiled in js binary. BUILD rule
 * can specify this value by "--define goog.LOCALE=<locale_name>" as a compiler
 * option.
 *
 * Take into account that the locale code format is important. You should use
 * the canonical Unicode format with hyphen as a delimiter. Language must be
 * lowercase, Language Script - Capitalized, Region - UPPERCASE.
 * There are few examples: pt-BR, en, en-US, sr-Latin-BO, zh-Hans-CN.
 *
 * See more info about locale codes here:
 * http://www.unicode.org/reports/tr35/#Unicode_Language_and_Locale_Identifiers
 *
 * For language codes you should use values defined by ISO 639-1. See it here
 * http://www.w3.org/WAI/ER/IG/ert/iso639.htm. There is only one exception from
 * this rule: the Hebrew language. For legacy reasons the old code (iw) should
 * be used instead of the new code (he).
 *
 * MOE:begin_intracomment_strip
 * See http://g3doc/i18n/identifiers/g3doc/synonyms.
 * MOE:end_intracomment_strip
 */
goog.LOCALE = goog.define('goog.LOCALE', 'en');  // default to en


/**
 * @define {boolean} Whether this code is running on trusted sites.
 *
 * On untrusted sites, several native functions can be defined or overridden by
 * external libraries like Prototype, Datejs, and JQuery and setting this flag
 * to false forces closure to use its own implementations when possible.
 *
 * If your JavaScript can be loaded by a third party site and you are wary about
 * relying on non-standard implementations, specify
 * "--define goog.TRUSTED_SITE=false" to the compiler.
 */
goog.TRUSTED_SITE = goog.define('goog.TRUSTED_SITE', true);


/**
 * @define {boolean} Whether code that calls {@link goog.setTestOnly} should
 *     be disallowed in the compilation unit.
 */
goog.DISALLOW_TEST_ONLY_CODE =
    goog.define('goog.DISALLOW_TEST_ONLY_CODE', COMPILED && !goog.DEBUG);


/**
 * @define {boolean} Whether to use a Chrome app CSP-compliant method for
 *     loading scripts via goog.require. @see appendScriptSrcNode_.
 */
goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING =
    goog.define('goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING', false);


// MOE:begin_strip
/**
 * Read a flag from the runtime flags object.
 * @param {number} googFlagId Enum ordinal
 * @param {boolean} defaultValue Value to return if the flag is not given
 * @return {boolean}
 */
goog.readFlagInternalDoNotUseOrElse = function(googFlagId, defaultValue) {
  var obj = goog.getObjectByName(goog.FLAGS_OBJECT_);
  var val = obj && obj[googFlagId];
  return val != null ? val : defaultValue;
};


/**
 * Name of the object to look for when looking up runtime flag values.  May be a
 * fully qualified object name (e.g. 'foo.bar').
 * @define {string}
 * @private
 */
goog.FLAGS_OBJECT_ = goog.define('goog.FLAGS_OBJECT', 'CLOSURE_FLAGS');


/**
 * Default value for the STAGING flag.  Defaults to `true`, indicating that
 * flags are enabled by default once they reach the STAGING lifecycle stage.
 * Risk-averse products should set this to `false` in their production builds.
 * This is only necessary for non-Boq products because Boq Web configures this
 * via the goog.flag system by default.
 *
 * @define {boolean}
 */
goog.FLAGS_STAGING_DEFAULT = goog.define('goog.FLAGS_STAGING_DEFAULT', true);

/**
 * Defines a local copy for multiple chunk set namespace isolation.
 *
 * @suppress {checkVars}
 */
goog.CLOSURE_TOGGLE_ORDINALS = typeof CLOSURE_TOGGLE_ORDINALS === 'object' ?
    CLOSURE_TOGGLE_ORDINALS :
    goog.global.CLOSURE_TOGGLE_ORDINALS;

/**
 * Read a toggle's value.  This should not be called directly.  Use the
 * `toggle_provider` build rule instead.  See go/toggle-provider.
 * @param {string} name
 * @return {boolean}
 */
goog.readToggleInternalDoNotCallDirectly = function(name) {
  var ordinals = goog.CLOSURE_TOGGLE_ORDINALS;
  var ordinal = ordinals && ordinals[name];
  if (typeof ordinal !== 'number') return Boolean(ordinal);
  return Boolean(
      goog.TOGGLES_[Math.floor(ordinal / 30)] & (1 << (ordinal % 30)));
};


/**
 * Bootstrap variable mapping toggle names to ordinals.  This is intended to be
 * read by JSCompiler to replace goog.readToggle...() calls with direct lookups,
 * but is also used by the debug-mode version of the toggle reader.
 * @const {!Object<string, number|boolean>|undefined}
 */
goog.global.CLOSURE_TOGGLE_ORDINALS;


/**
 * @define {string} Global variable to check for toggles.
 * @private
 */
goog.TOGGLE_VAR_ = goog.define('goog.TOGGLE_VAR', '_F_toggles');


/** @private @const {!Array<number>} */
goog.TOGGLES_ = goog.global[goog.TOGGLE_VAR_] || [];
// MOE:end_strip

/** @define {boolean} */
goog.GENDERED_MESSAGES_ENABLED =
    goog.define('goog.GENDERED_MESSAGES_ENABLED', true);

/** @private @enum {number} */
goog.GrammaticalGender_ = {
  OTHER: 0,
  MASCULINE: 1,
  FEMININE: 2,
  NEUTER: 3,
};

/**
 * See go/grammatical-gender-in-capabilities and
 * go/gender-appropriate-ui-jscompiler
 * @private @const {!Object<string, !goog.GrammaticalGender_>}
 */
goog.GRAMMATICAL_GENDER_MAP_ = {
  'FEMININE': goog.GrammaticalGender_.FEMININE,
  'MASCULINE': goog.GrammaticalGender_.MASCULINE,
  'NEUTER': goog.GrammaticalGender_.NEUTER,
};

/**
 * Defines a local copy of viewers grammatical gender for use in gendered
 * messages.  Unknown values are mapped to `OTHER`
 * @private @const {!goog.GrammaticalGender_}
 */
goog.viewerGrammaticalGender_ =
    goog.GRAMMATICAL_GENDER_MAP_[goog.GENDERED_MESSAGES_ENABLED && goog.global['_F_VIEWER_GRAMMATICAL_GENDER']] ||
    goog.GrammaticalGender_.OTHER;

/**
 * Shared constants for gendered messages based on the value of
 * `goog.viewerGrammaticalGender`
 */
/** @const */
goog.msgKind = {};

/**
 * @const
 * @noinline
 */
goog.msgKind.MASCULINE =
    (goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.MASCULINE);

/**
 * @const
 * @noinline
 */
goog.msgKind.FEMININE =
    (goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.FEMININE);

/**
 * @const
 * @noinline
 */
goog.msgKind.NEUTER =
    (goog.viewerGrammaticalGender_ === goog.GrammaticalGender_.NEUTER);

if (COMPILED && goog.LOCALE == '') {
  // This code should never execute.  It is here to ensure that the compiler
  // does not remove the values until goog.LOCALE is defined.
  goog.logToConsole_('' + [
    goog.msgKind.MASCULINE, goog.msgKind.FEMININE, goog.msgKind.NEUTER
  ]);
}

/**
 * A hook for providing an object that should be used to track the "legacy
 * namespaces". The legacy namespace is where symbols from `goog.provide` as
 * well as symbols from `goog.module` with
 * `goog.module.declareLegacyNamespace` are placed.
 *
 * If this isn't specified, `goog.global` will be considered the legacy
 * namespace object.
 *
 * @type {!Object|undefined}
 */
goog.global.CLOSURE_UNCOMPILED_LEGACY_NAMESPACE_OBJECT;


/**
 * @type {!Object}
 * @private
 */
goog.LEGACY_NAMESPACE_OBJECT_ =
    (!COMPILED &&
     typeof CLOSURE_UNCOMPILED_LEGACY_NAMESPACE_OBJECT !== 'undefined') ?
    CLOSURE_UNCOMPILED_LEGACY_NAMESPACE_OBJECT :
    goog.global;


/**
 * Defines a namespace in Closure.
 *
 * A namespace may only be defined once in a codebase. It may be defined using
 * goog.provide() or goog.module().
 *
 * The presence of one or more goog.provide() calls in a file indicates
 * that the file defines the given objects/namespaces.
 * Provided symbols must not be null or undefined.
 *
 * In addition, goog.provide() creates the object stubs for a namespace
 * (for example, goog.provide("goog.foo.bar") will create the object
 * goog.foo.bar if it does not already exist).
 *
 * Build tools also scan for provide/require/module statements
 * to discern dependencies, build dependency files (see deps.js), etc.
 *
 * @see goog.require
 * @see goog.module
 * @param {string} name Namespace provided by this file in the form
 *     "goog.package.part".
 * deprecated Use goog.module (see b/159289405)
 */
goog.provide = function(name) {
  if (goog.isInModuleLoader_()) {
    throw new Error('goog.provide cannot be used within a module.');
  }
  if (!COMPILED) {
    // Ensure that the same namespace isn't provided twice.
    // A goog.module/goog.provide maps a goog.require to a specific file
    if (goog.isProvided_(name)) {
      throw new Error('Namespace "' + name + '" already declared.');
    }
  }

  goog.constructNamespace_(name);
};


/**
 * @param {string} name Namespace provided by this file in the form
 *     "goog.package.part".
 * @param {?Object=} object The object to embed in the namespace.
 * @param {boolean=} overwriteImplicit If object is set and a previous call
 *     implicitly constructed the namespace given by name, this parameter
 *     controls whether opt_obj should overwrite the implicitly constructed
 *     namespace or be merged into it. Defaults to false.
 * @private
 */
goog.constructNamespace_ = function(name, object, overwriteImplicit) {
  if (!COMPILED) {
    delete goog.implicitNamespaces_[name];

    var namespace = name;
    while ((namespace = namespace.substring(0, namespace.lastIndexOf('.')))) {
      if (goog.getObjectByName(namespace, goog.LEGACY_NAMESPACE_OBJECT_)) {
        break;
      }
      goog.implicitNamespaces_[namespace] = true;
    }
  }

  goog.exportPath_(
      name, object, overwriteImplicit, goog.LEGACY_NAMESPACE_OBJECT_);
};


/**
 * According to the CSP3 spec a nonce must be a valid base64 string.
 * @see https://www.w3.org/TR/CSP3/#grammardef-base64-value
 * @private @const
 */
goog.NONCE_PATTERN_ = /^[\w+/_-]+[=]{0,2}$/;


/**
 * Returns CSP nonce, if set for any script tag.
 * @param {?Window=} opt_window The window context used to retrieve the nonce.
 *     Defaults to global context.
 * @return {string} CSP nonce or empty string if no nonce is present.
 * @private
 */
goog.getScriptNonce_ = function(opt_window) {
  var doc = (opt_window || goog.global).document;
  var script = doc.querySelector && doc.querySelector('script[nonce]');
  if (script) {
    // Try to get the nonce from the IDL property first, because browsers that
    // implement additional nonce protection features (currently only Chrome) to
    // prevent nonce stealing via CSS do not expose the nonce via attributes.
    // See https://github.com/whatwg/html/issues/2369
    var nonce = script['nonce'] || script.getAttribute('nonce');
    if (nonce && goog.NONCE_PATTERN_.test(nonce)) {
      return nonce;
    }
  }
  return '';
};


/**
 * Module identifier validation regexp.
 * Note: This is a conservative check, it is very possible to be more lenient,
 *   the primary exclusion here is "/" and "\" and a leading ".", these
 *   restrictions are intended to leave the door open for using goog.require
 *   with relative file paths rather than module identifiers.
 * @private
 */
goog.VALID_MODULE_RE_ = /^[a-zA-Z_$][a-zA-Z0-9._$]*$/;


/**
 * Defines a module in Closure.
 *
 * Marks that this file must be loaded as a module and claims the namespace.
 *
 * A namespace may only be defined once in a codebase. It may be defined using
 * goog.provide() or goog.module().
 *
 * goog.module() has three requirements:
 * - goog.module may not be used in the same file as goog.provide.
 * - goog.module must be the first statement in the file.
 * - only one goog.module is allowed per file.
 *
 * When a goog.module annotated file is loaded, it is enclosed in
 * a strict function closure. This means that:
 * - any variables declared in a goog.module file are private to the file
 * (not global), though the compiler is expected to inline the module.
 * - The code must obey all the rules of "strict" JavaScript.
 * - the file will be marked as "use strict"
 *
 * NOTE: unlike goog.provide, goog.module does not declare any symbols by
 * itself. If declared symbols are desired, use
 * goog.module.declareLegacyNamespace().
 *
 * MOE:begin_intracomment_strip
 * See the goog.module announcement at http://go/goog.module-announce
 * MOE:end_intracomment_strip
 *
 * See the public goog.module proposal: http://goo.gl/Va1hin
 *
 * @param {string} name Namespace provided by this file in the form
 *     "goog.package.part", is expected but not required.
 * @return {void}
 */
goog.module = function(name) {
  if (COMPILED) {
    // In the optimized code, goog.module calls are complete removed but
    // due to b/389129315 the function itself is retained.
    return;
  }
  if (typeof name !== 'string' || !name ||
      name.search(goog.VALID_MODULE_RE_) == -1) {
    throw new Error('Invalid module identifier');
  }
  if (!goog.isInGoogModuleLoader_()) {
    throw new Error(
        'Module ' + name + ' has been loaded incorrectly. Note, ' +
        'modules cannot be loaded as normal scripts. They require some kind of ' +
        'pre-processing step. You\'re likely trying to load a module via a ' +
        'script tag or as a part of a concatenated bundle without rewriting the ' +
        'module. For more info see: ' +
        'https://github.com/google/closure-library/wiki/goog.module:-an-ES6-module-like-alternative-to-goog.provide.');
  }
  if (goog.moduleLoaderState_.moduleName) {
    throw new Error('goog.module may only be called once per module.');
  }

  // Store the module name for the loader.
  goog.moduleLoaderState_.moduleName = name;
  // Ensure that the same namespace isn't provided twice.
  // A goog.module/goog.provide maps a goog.require to a specific file
  if (goog.isProvided_(name)) {
    throw new Error('Namespace "' + name + '" already declared.');
  }
  delete goog.implicitNamespaces_[name];
};


/**
 * @param {string} name The module identifier.
 * @return {?} The module exports for an already loaded module or null.
 *
 * Note: This is not an alternative to goog.require, it does not
 * indicate a hard dependency, instead it is used to indicate
 * an optional dependency or to access the exports of a module
 * that has already been loaded.
 * @suppress {missingProvide}
 */
goog.module.get = function(name) {
  return COMPILED ? null : goog.module.getInternal_(name);
};


/**
 * @param {string} name The module identifier.
 * @return {?} The module exports for an already loaded module or null.
 * @private
 */
goog.module.getInternal_ = function(name) {
  if (!COMPILED) {
    if (name in goog.loadedModules_) {
      return goog.loadedModules_[name].exports;
    } else if (!goog.implicitNamespaces_[name]) {
      var ns = goog.getObjectByName(name, goog.LEGACY_NAMESPACE_OBJECT_);
      return ns != null ? ns : null;
    }
  }
  return null;
};

// MOE:begin_strip
/**
 * Defines dynamic import execution path for uncompiled mode.
 *
 * @param {string} name The module identifier.
 * @return {?} The module exports for an already loaded module or null.
 *
 * NOTE: In compiled code, JsCompiler will transpile this function call.
 * DO NOT OPENSOURCE
 */
goog.requireDynamic = function(name) {
  if (!COMPILED) {
    if (!goog.importHandler_ || !goog.uncompiledChunkIdHandler_) {
      throw new Error('Need to setup import handler and chunk id handler.');
    }
    return goog.importHandler_(goog.uncompiledChunkIdHandler_(name))
        .then(function() {
          var module = goog.module.getInternal_(name);
          if (module == null) {
            throw new Error('Module ' + name + ' is not loaded.');
          }
          return module;
        });
  }
  return null;
};


/**
 * Handler for dynamic import.
 * DO NOT OPENSOURCE
 */
goog.importHandler_ = null;


/**
 * Chunk ID calculator.
 * @private {?function(string)}
 * DO NOT OPENSOURCE
 */
goog.uncompiledChunkIdHandler_ = null;


/**
 * Sets import handler.
 * @param {function(string)} fn
 * DO NOT OPENSOURCE
 */
goog.setImportHandlerInternalDoNotCallOrElse = function(fn) {
  goog.importHandler_ = fn;
};


/**
 * Sets chunk ID calculator.
 * @param {function(string)} fn
 * NOTE: The chunk ID calculator is only used in uncompiled mode.
 * DO NOT OPENSOURCE
 */
goog.setUncompiledChunkIdHandlerInternalDoNotCallOrElse = function(fn) {
  goog.uncompiledChunkIdHandler_ = fn;
};


/**
 * This exists purely as a hint to JsTrimmer, so that it can convert it to
 * goog.require in certain circumstances.
 *
 * @param {string} namespace
 * DO NOT OPENSOURCE
 */
goog.maybeRequireFrameworkInternalOnlyDoNotCallOrElse = function(namespace) {};
// MOE:end_strip

/**
 * Types of modules the debug loader can load.
 * @enum {string}
 */
goog.ModuleType = {
  ES6: 'es6',
  GOOG: 'goog'
};


/**
 * @private {?{
 *   moduleName: (string|undefined),
 *   declareLegacyNamespace:boolean,
 *   preventModuleExportSealing:boolean,
 *   type: ?goog.ModuleType
 * }}
 */
goog.moduleLoaderState_ = null;


/**
 * @private
 * @return {boolean} Whether a goog.module or an es6 module is currently being
 *     initialized.
 */
goog.isInModuleLoader_ = function() {
  return goog.isInGoogModuleLoader_() || goog.isInEs6ModuleLoader_();
};


/**
 * @private
 * @return {boolean} Whether a goog.module is currently being initialized.
 */
goog.isInGoogModuleLoader_ = function() {
  return !!goog.moduleLoaderState_ &&
      goog.moduleLoaderState_.type == goog.ModuleType.GOOG;
};


/**
 * @private
 * @return {boolean} Whether an es6 module is currently being initialized.
 */
goog.isInEs6ModuleLoader_ = function() {
  var inLoader = !!goog.moduleLoaderState_ &&
      goog.moduleLoaderState_.type == goog.ModuleType.ES6;

  if (inLoader) {
    return true;
  }

  var jscomp = goog.LEGACY_NAMESPACE_OBJECT_['$jscomp'];

  if (jscomp) {
    // jscomp may not have getCurrentModulePath if this is a compiled bundle
    // that has some of the runtime, but not all of it. This can happen if
    // optimizations are turned on so the unused runtime is removed but renaming
    // and Closure pass are off (so $jscomp is still named $jscomp and the
    // goog.provide/require calls still exist).
    if (typeof jscomp.getCurrentModulePath != 'function') {
      return false;
    }

    // Bundled ES6 module.
    return !!jscomp.getCurrentModulePath();
  }

  return false;
};


/**
 * Provide the module's exports as a globally accessible object under the
 * module's declared name.  This is intended to ease migration to goog.module
 * for files that have existing usages.
 * @suppress {missingProvide}
 */
goog.module.declareLegacyNamespace = function() {
  if (!COMPILED && !goog.isInGoogModuleLoader_()) {
    throw new Error(
        'goog.module.declareLegacyNamespace must be called from ' +
        'within a goog.module');
  }
  if (!COMPILED && !goog.moduleLoaderState_.moduleName) {
    throw new Error(
        'goog.module must be called prior to ' +
        'goog.module.declareLegacyNamespace.');
  }
  goog.moduleLoaderState_.declareLegacyNamespace = true;
};


/**
 * Ensures that a module's exports object is not sealed after the module is
 * evaluated.
 * @suppress {missingProvide}
 */
goog.module.preventModuleExportSealing = function() {
  if (!COMPILED && !goog.isInGoogModuleLoader_()) {
    throw new Error(
        'goog.module.preventModuleExportSealing must be called from ' +
        'within a goog.module');
  }
  if (!COMPILED && !goog.moduleLoaderState_.moduleName) {
    throw new Error(
        'goog.module must be called prior to ' +
        'goog.module.preventModuleExportSealing.');
  }
  goog.moduleLoaderState_.preventModuleExportSealing = true;
};


/**
 * Associates an ES6 module with a Closure module ID so that is available via
 * goog.require. The associated ID  acts like a goog.module ID - it does not
 * create any global names, it is merely available via goog.require /
 * goog.module.get / goog.forwardDeclare / goog.requireType. goog.require and
 * goog.module.get will return the entire module as if it was import *'d. This
 * allows Closure files to reference ES6 modules for the sake of migration.
 *
 * @param {string} namespace
 * @suppress {missingProvide}
 */
goog.declareModuleId = function(namespace) {
  if (!COMPILED) {
    if (!goog.isInEs6ModuleLoader_()) {
      throw new Error(
          'goog.declareModuleId may only be called from ' +
          'within an ES6 module');
    }
    if (goog.moduleLoaderState_ && goog.moduleLoaderState_.moduleName) {
      throw new Error(
          'goog.declareModuleId may only be called once per module.');
    }
    if (namespace in goog.loadedModules_) {
      throw new Error(
          'Module with namespace "' + namespace + '" already exists.');
    }
  }
  if (goog.moduleLoaderState_) {
    // Not bundled - debug loading.
    goog.moduleLoaderState_.moduleName = namespace;
  } else {
    // Bundled - not debug loading, no module loader state.
    var jscomp = goog.LEGACY_NAMESPACE_OBJECT_['$jscomp'];
    if (!jscomp || typeof jscomp.getCurrentModulePath != 'function') {
      throw new Error(
          'Module with namespace "' + namespace +
          '" has been loaded incorrectly.');
    }
    var exports = jscomp.require(jscomp.getCurrentModulePath());
    goog.loadedModules_[namespace] = {
      exports: exports,
      type: goog.ModuleType.ES6,
      moduleId: namespace
    };
  }
};


/**
 * Marks that the current file should only be used for testing, and never for
 * live code in production.
 *
 * In the case of unit tests, the message may optionally be an exact namespace
 * for the test (e.g. 'goog.stringTest'). The linter will then ignore the extra
 * provide (if not explicitly defined in the code).
 *
 * @param {string=} opt_message Optional message to add to the error that's
 *     raised when used in production code.
 */
goog.setTestOnly = function(opt_message) {
  if (goog.DISALLOW_TEST_ONLY_CODE) {
    opt_message = opt_message || '';
    throw new Error(
        'Importing test-only code into non-debug environment' +
        (opt_message ? ': ' + opt_message : '.'));
  }
};


/**
 * Forward declares a symbol. This is an indication to the compiler that the
 * symbol may be used in the source yet is not required and may not be provided
 * in compilation.
 *
 * The most common usage of forward declaration is code that takes a type as a
 * function parameter but does not need to require it. By forward declaring
 * instead of requiring, no hard dependency is made, and (if not required
 * elsewhere) the namespace may never be required and thus, not be pulled
 * into the JavaScript binary. If it is required elsewhere, it will be type
 * checked as normal.
 *
 * Before using goog.forwardDeclare, please read the documentation at
 * https://github.com/google/closure-compiler/wiki/Bad-Type-Annotation to
 * understand the options and tradeoffs when working with forward declarations.
 *
 * @param {string} name The namespace to forward declare in the form of
 *     "goog.package.part".
 * @deprecated See go/noforwarddeclaration, Use `goog.requireType` instead.
 */
goog.forwardDeclare = function(name) {};

if (!COMPILED) {
  /**
   * Check if the given name has been goog.provided. This will return false for
   * names that are available only as implicit namespaces.
   * @param {string} name name of the object to look for.
   * @return {boolean} Whether the name has been provided.
   * @private
   */
  goog.isProvided_ = function(name) {
    return (name in goog.loadedModules_) ||
        (!goog.implicitNamespaces_[name] &&
         goog.getObjectByName(name, goog.LEGACY_NAMESPACE_OBJECT_) != null);
  };

  /**
   * Namespaces implicitly defined by goog.provide. For example,
   * goog.provide('goog.events.Event') implicitly declares that 'goog' and
   * 'goog.events' must be namespaces.
   *
   * @type {!Object<string, (boolean|undefined)>}
   * @private
   */
  goog.implicitNamespaces_ = {'goog.module': true};

  // NOTE: We add goog.module as an implicit namespace as goog.module is defined
  // here and because the existing module package has not been moved yet out of
  // the goog.module namespace. This satisfies both the debug loader and
  // ahead-of-time dependency management.
}


/**
 * Returns an object based on its fully qualified external name.  The object
 * is not found if null or undefined.  If you are using a compilation pass that
 * renames property names beware that using this function will not find renamed
 * properties.
 *
 * @param {string} name The fully qualified name.
 * @param {Object=} opt_obj The object within which to look; default is
 *     |goog.global|.
 * @return {?} The value (object or primitive) or, if not found, null.
 */
goog.getObjectByName = function(name, opt_obj) {
  var parts = name.split('.');
  var cur = opt_obj || goog.global;
  for (var i = 0; i < parts.length; i++) {
    cur = cur[parts[i]];
    if (cur == null) {
      return null;
    }
  }
  return cur;
};


/**
 * Adds a dependency from a file to the files it requires.
 * @param {string} relPath The path to the js file.
 * @param {!Array<string>} provides An array of strings with
 *     the names of the objects this file provides.
 * @param {!Array<string>} requires An array of strings with
 *     the names of the objects this file requires.
 * @param {boolean|!Object<string>=} opt_loadFlags Parameters indicating
 *     how the file must be loaded.  The boolean 'true' is equivalent
 *     to {'module': 'goog'} for backwards-compatibility.  Valid properties
 *     and values include {'module': 'goog'} and {'lang': 'es6'}.
 */
goog.addDependency = function(relPath, provides, requires, opt_loadFlags) {
  if (!COMPILED && goog.DEPENDENCIES_ENABLED) {
    goog.debugLoader_.addDependency(relPath, provides, requires, opt_loadFlags);
  }
};


// NOTE(nnaze): The debug DOM loader was included in base.js as an original way
// to do "debug-mode" development.  The dependency system can sometimes be
// confusing, as can the debug DOM loader's asynchronous nature.
//
// With the DOM loader, a call to goog.require() is not blocking -- the script
// will not load until some point after the current script.  If a namespace is
// needed at runtime, it needs to be defined in a previous script, or loaded via
// require() with its registered dependencies.
//
// User-defined namespaces may need their own deps file. For a reference on
// creating a deps file, see:
// MOE:begin_strip
// Internally: http://go/deps-files and http://go/be#js_deps
// MOE:end_strip
// Externally: https://developers.google.com/closure/library/docs/depswriter
//
// Because of legacy clients, the DOM loader can't be easily removed from
// base.js.  Work was done to make it disableable or replaceable for
// different environments (DOM-less JavaScript interpreters like Rhino or V8,
// for example). See bootstrap/ for more information.


/**
 * @define {boolean} Whether to enable the debug loader.
 *
 * If enabled, a call to goog.require() will attempt to load the namespace by
 * appending a script tag to the DOM (if the namespace has been registered).
 *
 * If disabled, goog.require() will simply assert that the namespace has been
 * provided (and depend on the fact that some outside tool correctly ordered
 * the script).
 */
goog.ENABLE_DEBUG_LOADER = goog.define('goog.ENABLE_DEBUG_LOADER', false);


/**
 * @param {string} msg
 * @private
 */
goog.logToConsole_ = function(msg) {
  if (goog.global.console) {
    goog.global.console['error'](msg);
  }
};


/**
 * Implements a system for the dynamic resolution of dependencies that works in
 * parallel with the BUILD system.
 *
 * Note that all calls to goog.require will be stripped by the compiler.
 *
 * @see goog.provide
 * @param {string} namespace Namespace (as was given in goog.provide,
 *     goog.module, or goog.declareModuleId) in the form
 *     "goog.package.part".
 * @return {?} If called within a goog.module or ES6 module file, the associated
 *     namespace or module otherwise null.
 */
goog.require = function(namespace) {
  if (!COMPILED) {
    // Might need to lazy load on old IE.
    if (goog.ENABLE_DEBUG_LOADER) {
      goog.debugLoader_.requested(namespace);
    }

    // If the object already exists we do not need to do anything.
    if (goog.isProvided_(namespace)) {
      if (goog.isInModuleLoader_()) {
        return goog.module.getInternal_(namespace);
      }
    } else if (goog.ENABLE_DEBUG_LOADER) {
      var moduleLoaderState = goog.moduleLoaderState_;
      goog.moduleLoaderState_ = null;
      try {
        goog.debugLoader_.load_(namespace);
      } finally {
        goog.moduleLoaderState_ = moduleLoaderState;
      }
    }

    return null;
  }
};


/**
 * Requires a symbol for its type information. This is an indication to the
 * compiler that the symbol may appear in type annotations, yet it is not
 * referenced at runtime.
 *
 * When called within a goog.module or ES6 module file, the return value may be
 * assigned to or destructured into a variable, but it may not be otherwise used
 * in code outside of a type annotation.
 *
 * Note that all calls to goog.requireType will be stripped by the compiler.
 *
 * @param {string} namespace Namespace (as was given in goog.provide,
 *     goog.module, or goog.declareModuleId) in the form
 *     "goog.package.part".
 * @return {?}
 */
goog.requireType = function(namespace) {
  // Return an empty object so that single-level destructuring of the return
  // value doesn't crash at runtime when using the debug loader. Multi-level
  // destructuring isn't supported.
  return {};
};


/**
 * Path for included scripts.
 * @type {string}
 */
goog.basePath = '';


/**
 * A hook for overriding the base path.
 * @type {string|undefined}
 */
goog.global.CLOSURE_BASE_PATH;


/**
 * A function to import a single script. This is meant to be overridden when
 * Closure is being run in non-HTML contexts, such as web workers. It's defined
 * in the global scope so that it can be set before base.js is loaded, which
 * allows deps.js to be imported properly.
 *
 * The first parameter the script source, which is a relative URI. The second,
 * optional parameter is the script contents, in the event the script needed
 * transformation. It should return true if the script was imported, false
 * otherwise.
 * @type {(function(string, string=): boolean)|undefined}
 */
goog.global.CLOSURE_IMPORT_SCRIPT;


/**
 * When defining a class Foo with an abstract method bar(), you can do:
 * Foo.prototype.bar = goog.abstractMethod
 *
 * Now if a subclass of Foo fails to override bar(), an error will be thrown
 * when bar() is invoked.
 *
 * @type {!Function}
 * @throws {Error} when invoked to indicate the method should be overridden.
 * @deprecated Use "@abstract" annotation instead of goog.abstractMethod in new
 *     code. See
 *     https://github.com/google/closure-compiler/wiki/@abstract-classes-and-methods
 */
goog.abstractMethod = function() {
  throw new Error('unimplemented abstract method');
};


/**
 * Adds a `getInstance` static method that always returns the same
 * instance object.
 * @param {!Function} ctor The constructor for the class to add the static
 *     method to.
 * @suppress {missingProperties} 'instance_' isn't a property on 'Function'
 *     but we don't have a better type to use here.
 */
goog.addSingletonGetter = function(ctor) {
  // instance_ is immediately set to prevent issues with sealed constructors
  // such as are encountered when a constructor is returned as the export object
  // of a goog.module in unoptimized code.
  // Declare type to avoid conformance violations that ctor.instance_ is unknown
  /** @type {undefined|!Object} @suppress {underscore} */
  ctor.instance_ = undefined;
  ctor.getInstance = function() {
    if (ctor.instance_) {
      return ctor.instance_;
    }
    if (goog.DEBUG) {
      // NOTE: JSCompiler can't optimize away Array#push.
      goog.instantiatedSingletons_[goog.instantiatedSingletons_.length] = ctor;
    }
    // Cast to avoid conformance violations that ctor.instance_ is unknown
    return /** @type {!Object|undefined} */ (ctor.instance_) = new ctor;
  };
};


/**
 * All singleton classes that have been instantiated, for testing. Don't read
 * it directly, use the `goog.testing.singleton` module. The compiler
 * removes this variable if unused.
 * @type {!Array<!Function>}
 * @private
 */
goog.instantiatedSingletons_ = [];


/**
 * @define {boolean} Whether to load goog.modules using `eval` when using
 * the debug loader.  This provides a better debugging experience as the
 * source is unmodified and can be edited using Chrome Workspaces or similar.
 * However in some environments the use of `eval` is banned
 * so we provide an alternative.
 */
goog.LOAD_MODULE_USING_EVAL = goog.define('goog.LOAD_MODULE_USING_EVAL', true);


/**
 * @define {boolean} Whether the exports of goog.modules should be sealed when
 * possible.
 */
goog.SEAL_MODULE_EXPORTS = goog.define('goog.SEAL_MODULE_EXPORTS', goog.DEBUG);


/**
 * Hidden symbol used to mark an object being used as the Closure module
 * object so that the debug loader does not seal the object and prevent new
 * properties from being defined on it.
 * @private @const {?symbol}
 */
goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ =
    typeof Symbol === 'function' ? Symbol('preventModuleExportSealing') : null;



/**
 * The registry of initialized modules:
 * The module identifier or path to module exports map.
 * @private @const {!Object<string, {exports:?,type:string,moduleId:string}>}
 */
goog.loadedModules_ = {};


/**
 * True if the debug loader enabled and used.
 * @const {boolean}
 */
goog.DEPENDENCIES_ENABLED = !COMPILED && goog.ENABLE_DEBUG_LOADER;



/**
 * @define {boolean} If true assume that ES modules have already been
 * transpiled by the jscompiler (in the same way that transpile.js would
 * transpile them - to jscomp modules). Useful only for servers that wish to use
 * the debug loader and transpile server side. Thus this is only respected if
 * goog.TRANSPILE is "never".
 */
goog.ASSUME_ES_MODULES_TRANSPILED =
    goog.define('goog.ASSUME_ES_MODULES_TRANSPILED', false);


/**
 * @define {string} Trusted Types policy name. If non-empty then Closure will
 * use Trusted Types.
 */
goog.TRUSTED_TYPES_POLICY_NAME =
    goog.define('goog.TRUSTED_TYPES_POLICY_NAME', 'goog');


/**
 * @param {function(?):?|string} moduleDef The module definition.
 */
goog.loadModule = function(moduleDef) {
  // NOTE: we allow function definitions to be either in the from
  // of a string to eval (which keeps the original source intact) or
  // in a eval forbidden environment (CSP) we allow a function definition
  // which in its body must call `goog.module`, and return the exports
  // of the module.
  var previousState = goog.moduleLoaderState_;
  try {
    goog.moduleLoaderState_ = {
      moduleName: '',
      declareLegacyNamespace: false,
      preventModuleExportSealing: false,
      type: goog.ModuleType.GOOG
    };
    var origExports = {};
    var exports = origExports;
    if (typeof moduleDef === 'function') {
      exports = moduleDef.call(undefined, exports);
    } else if (typeof moduleDef === 'string') {
      exports = goog.loadModuleFromSource_.call(undefined, exports, moduleDef);
    } else {
      throw new Error('Invalid module definition');
    }

    var moduleName = goog.moduleLoaderState_.moduleName;
    if (typeof moduleName === 'string' && moduleName) {
      // Don't seal legacy namespaces as they may be used as a parent of
      // another namespace
      if (goog.moduleLoaderState_.declareLegacyNamespace) {
        // Whether exports was overwritten via default export assignment.
        // This is important for legacy namespaces as it dictates whether
        // previously a previously loaded implicit namespace should be clobbered
        // or not.
        var isDefaultExport = origExports !== exports;
        goog.constructNamespace_(moduleName, exports, isDefaultExport);
      } else if (
          goog.SEAL_MODULE_EXPORTS && Object.seal &&
          typeof exports == 'object' && exports != null) {
        if (goog.moduleLoaderState_.preventModuleExportSealing) {
          if (goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ &&
              Object.defineProperty) {
            try {
              // Keep configurable: true so the descriptor remains redefinable
              // if downstream modules or tests need to reconfigure the exports
              // object.
              Object.defineProperty(
                  exports, goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_, {
                    value: true,
                    writable: false,
                    enumerable: false,
                    configurable: true,
                  });
            } catch (e) {
              // Ignore if the exports object cannot be mutated.
            }
          }
        } else if (!(goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_ &&
                     Object.prototype.hasOwnProperty.call(
                         exports,
                         goog.PREVENT_MODULE_EXPORTS_SEALING_SYMBOL_))) {
          Object.seal(exports);
        }
      }

      var data = {
        exports: exports,
        type: goog.ModuleType.GOOG,
        moduleId: goog.moduleLoaderState_.moduleName
      };
      goog.loadedModules_[moduleName] = data;
    } else {
      throw new Error('Invalid module name \"' + moduleName + '\"');
    }
  } finally {
    goog.moduleLoaderState_ = previousState;
  }
};


/**
 * @private @const
 */
goog.loadModuleFromSource_ =
    /** @type {function(!Object, string):?} */ (function(exports) {
      // NOTE: we avoid declaring parameters or local variables here to avoid
      // masking globals or leaking values into the module definition.
      'use strict';
      eval(goog.CLOSURE_EVAL_PREFILTER_.createScript(arguments[1]));
      return exports;
    });


/**
 * Normalize a file path by removing redundant ".." and extraneous "." file
 * path components.
 * @param {string} path
 * @return {string}
 * @private
 */
goog.normalizePath_ = function(path) {
  var components = path.split('/');
  var i = 0;
  while (i < components.length) {
    if (components[i] == '.') {
      components.splice(i, 1);
    } else if (
        i && components[i] == '..' && components[i - 1] &&
        components[i - 1] != '..') {
      components.splice(--i, 2);
    } else {
      i++;
    }
  }
  return components.join('/');
};


/**
 * Provides a hook for loading a file when using Closure's goog.require() API
 * with goog.modules.  In particular this hook is provided to support Node.js.
 *
 * @type {(function(string):string)|undefined}
 */
goog.global.CLOSURE_LOAD_FILE_SYNC;


/**
 * Loads file by synchronous XHR. Should not be used in production environments.
 * @param {string} src Source URL.
 * @return {?string} File contents, or null if load failed.
 * @private
 */
goog.loadFileSync_ = function(src) {
  if (goog.global.CLOSURE_LOAD_FILE_SYNC) {
    return goog.global.CLOSURE_LOAD_FILE_SYNC(src);
  } else {
    try {
      /** @type {XMLHttpRequest} */
      var xhr = new goog.global['XMLHttpRequest']();
      xhr.open('get', src, false);
      xhr.send();
      // NOTE: Successful http: requests have a status of 200, but successful
      // file: requests may have a status of zero.  Any other status, or a
      // thrown exception (particularly in case of file: requests) indicates
      // some sort of error, which we treat as a missing or unavailable file.
      return xhr.status == 0 || xhr.status == 200 ? xhr.responseText : null;
    } catch (err) {
      // No need to rethrow or log, since errors should show up on their own.
      return null;
    }
  }
};

//==============================================================================
// Language Enhancements
//==============================================================================


/**
 * This is a "fixed" version of the typeof operator.  It differs from the typeof
 * operator in such a way that null returns 'null' and arrays return 'array'.
 * @param {?} value The value to get the type of.
 * @return {string} The name of the type.
 */
goog.typeOf = function(value) {
  var s = typeof value;

  if (s != 'object') {
    return s;
  }

  if (!value) {
    return 'null';
  }

  if (Array.isArray(value)) {
    return 'array';
  }
  return s;
};


/**
 * Returns true if the object looks like an array. To qualify as array like
 * the value needs to be either a NodeList or an object with a Number length
 * property. Note that for this function neither strings nor functions are
 * considered "array-like".
 *
 * @param {?} val Variable to test.
 * @return {boolean} Whether variable is an array.
 */
goog.isArrayLike = function(val) {
  var type = goog.typeOf(val);
  // We do not use goog.isObject here in order to exclude function values.
  return type == 'array' || type == 'object' && typeof val.length == 'number';
};


/**
 * Returns true if the object looks like a Date. To qualify as Date-like the
 * value needs to be an object and have a getFullYear() function.
 * @param {?} val Variable to test.
 * @return {boolean} Whether variable is a like a Date.
 */
goog.isDateLike = function(val) {
  return goog.isObject(val) && typeof val.getFullYear == 'function';
};


/**
 * Returns true if the specified value is an object.  This includes arrays and
 * functions.
 * @param {?} val Variable to test.
 * @return {boolean} Whether variable is an object.
 */
goog.isObject = function(val) {
  var type = typeof val;
  return type == 'object' && val != null || type == 'function';
  // return Object(val) === val also works, but is slower, especially if val is
  // not an object.
};


/**
 * Gets a unique ID for an object. This mutates the object so that further calls
 * with the same object as a parameter returns the same value. The unique ID is
 * guaranteed to be unique across the current session amongst objects that are
 * passed into `getUid`. There is no guarantee that the ID is unique or
 * consistent across sessions. It is unsafe to generate unique ID for function
 * prototypes.
 *
 * @param {Object} obj The object to get the unique ID for.
 * @return {number} The unique ID for the object.
 */
goog.getUid = function(obj) {
  // TODO: Make the type stricter, do not accept null.
  return Object.prototype.hasOwnProperty.call(obj, goog.UID_PROPERTY_) &&
      obj[goog.UID_PROPERTY_] ||
      (obj[goog.UID_PROPERTY_] = ++goog.uidCounter_);
};


/**
 * Whether the given object is already assigned a unique ID.
 *
 * This does not modify the object.
 *
 * @param {!Object} obj The object to check.
 * @return {boolean} Whether there is an assigned unique id for the object.
 */
goog.hasUid = function(obj) {
  return !!obj[goog.UID_PROPERTY_];
};


/**
 * Removes the unique ID from an object. This is useful if the object was
 * previously mutated using `goog.getUid` in which case the mutation is
 * undone.
 * @param {Object} obj The object to remove the unique ID field from.
 */
goog.removeUid = function(obj) {
  // TODO: Make the type stricter, do not accept null.

  // In IE, DOM nodes are not instances of Object and throw an exception if we
  // try to delete.  Instead we try to use removeAttribute.
  if (obj !== null && 'removeAttribute' in obj) {
    obj.removeAttribute(goog.UID_PROPERTY_);
  }

  try {
    delete obj[goog.UID_PROPERTY_];
  } catch (ex) {
  }
};


/**
 * Name for unique ID property. Initialized in a way to help avoid collisions
 * with other closure JavaScript on the same page.
 * @type {string}
 * @private
 */
goog.UID_PROPERTY_ = 'closure_uid_' + ((Math.random() * 1e9) >>> 0);


/**
 * Counter for UID.
 * @type {number}
 * @private
 */
goog.uidCounter_ = 0;


/**
 * Clones a value. The input may be an Object, Array, or basic type. Objects and
 * arrays will be cloned recursively.
 *
 * WARNINGS:
 * <code>goog.cloneObject</code> does not detect reference loops. Objects that
 * refer to themselves will cause infinite recursion.
 *
 * <code>goog.cloneObject</code> is unaware of unique identifiers, and copies
 * UIDs created by <code>getUid</code> into cloned results.
 *
 * @param {*} obj The value to clone.
 * @return {*} A clone of the input value.
 * @deprecated goog.cloneObject is unsafe. Prefer the goog.object methods.
 */
goog.cloneObject = function(obj) {
  var type = goog.typeOf(obj);
  if (type == 'object' || type == 'array') {
    if (typeof obj.clone === 'function') {
      return obj.clone();
    }
    if (typeof Map !== 'undefined' && obj instanceof Map) {
      return new Map(obj);
    } else if (typeof Set !== 'undefined' && obj instanceof Set) {
      return new Set(obj);
    }
    var clone = type == 'array' ? [] : {};
    for (var key in obj) {
      clone[key] = goog.cloneObject(obj[key]);
    }
    return clone;
  }

  return obj;
};


/**
 * A native implementation of goog.bind.
 * @param {?function(this:T, ...)} fn A function to partially apply.
 * @param {T} selfObj Specifies the object which this should point to when the
 *     function is run.
 * @param {...*} var_args Additional arguments that are partially applied to the
 *     function.
 * @return {!Function} A partially-applied form of the function goog.bind() was
 *     invoked as a method of.
 * @template T
 * @private
 */
goog.bindNative_ = function(fn, selfObj, var_args) {
  return /** @type {!Function} */ (fn.call.apply(fn.bind, arguments));
};


/**
 * A pure-JS implementation of goog.bind.
 * @param {?function(this:T, ...)} fn A function to partially apply.
 * @param {T} selfObj Specifies the object which this should point to when the
 *     function is run.
 * @param {...*} var_args Additional arguments that are partially applied to the
 *     function.
 * @return {!Function} A partially-applied form of the function goog.bind() was
 *     invoked as a method of.
 * @template T
 * @private
 */
goog.bindJs_ = function(fn, selfObj, var_args) {
  if (!fn) {
    throw new Error();
  }

  if (arguments.length > 2) {
    var boundArgs = Array.prototype.slice.call(arguments, 2);
    return function() {
      // Prepend the bound arguments to the current arguments.
      var newArgs = Array.prototype.slice.call(arguments);
      Array.prototype.unshift.apply(newArgs, boundArgs);
      return fn.apply(selfObj, newArgs);
    };

  } else {
    return function() {
      return fn.apply(selfObj, arguments);
    };
  }
};


/**
 * Partially applies this function to a particular 'this object' and zero or
 * more arguments. The result is a new function with some arguments of the first
 * function pre-filled and the value of this 'pre-specified'.
 *
 * Remaining arguments specified at call-time are appended to the pre-specified
 * ones.
 *
 * Also see: {@link #partial}.
 *
 * Usage:
 * <pre>var barMethBound = goog.bind(myFunction, myObj, 'arg1', 'arg2');
 * barMethBound('arg3', 'arg4');</pre>
 *
 * @param {?function(this:T, ...)} fn A function to partially apply.
 * @param {T} selfObj Specifies the object which this should point to when the
 *     function is run.
 * @param {...*} var_args Additional arguments that are partially applied to the
 *     function.
 * @return {!Function} A partially-applied form of the function goog.bind() was
 *     invoked as a method of.
 * @template T
 * @suppress {deprecated} See above.
 * @deprecated use `=> {}` or Function.prototype.bind instead.
 */
goog.bind = function(fn, selfObj, var_args) {
  // TODO: narrow the type signature.
  if ((goog.TRUSTED_SITE && goog.FEATURESET_YEAR > 2012) ||
      (Function.prototype.bind &&
       // NOTE(nicksantos): Somebody pulled base.js into the default Chrome
       // extension environment. This means that for Chrome extensions, they get
       // the implementation of Function.prototype.bind that calls goog.bind
       // instead of the native one. Even worse, we don't want to introduce a
       // circular dependency between goog.bind and Function.prototype.bind, so
       // we have to hack this to make sure it works correctly.
       Function.prototype.bind.toString().indexOf('native code') != -1)) {
    goog.bind = goog.bindNative_;
  } else {
    goog.bind = goog.bindJs_;
  }
  return goog.bind.apply(null, arguments);
};


/**
 * Like goog.bind(), except that a 'this object' is not required. Useful when
 * the target function is already bound.
 *
 * Usage:
 * var g = goog.partial(f, arg1, arg2);
 * g(arg3, arg4);
 *
 * @param {Function} fn A function to partially apply.
 * @param {...*} var_args Additional arguments that are partially applied to fn.
 * @return {!Function} A partially-applied form of the function goog.partial()
 *     was invoked as a method of.
 */
goog.partial = function(fn, var_args) {
  var args = Array.prototype.slice.call(arguments, 1);
  return function() {
    // Clone the array (with slice()) and append additional arguments
    // to the existing arguments.
    var newArgs = args.slice();
    newArgs.push.apply(newArgs, arguments);
    return fn.apply(/** @type {?} */ (this), newArgs);
  };
};


/**
 * @return {number} An integer value representing the number of milliseconds
 *     between midnight, January 1, 1970 and the current time.
 * @deprecated Use Date.now
 */
goog.now = function() {
  return Date.now();
};


/**
 * Evals JavaScript in the global scope.
 *
 * Throws an exception if eval is not defined.
 * @param {string|!TrustedScript} script JavaScript string.
 */
goog.globalEval = function(script) {
  (0, eval)(script);
};


/**
 * Optional map of CSS class names to obfuscated names used with
 * goog.getCssName().
 * @private {!Object<string, string>|undefined}
 * @see goog.setCssNameMapping
 */
goog.cssNameMapping_;


/**
 * Optional obfuscation style for CSS class names. Should be set to either
 * 'BY_WHOLE' or 'BY_PART' if defined.
 * @type {string|undefined}
 * @private
 * @see goog.setCssNameMapping
 */
goog.cssNameMappingStyle_;



/**
 * A hook for modifying the default behavior goog.getCssName. The function
 * if present, will receive the standard output of the goog.getCssName as
 * its input.
 *
 * @type {(function(string):string)|undefined}
 */
goog.global.CLOSURE_CSS_NAME_MAP_FN;


/**
 * Handles strings that are intended to be used as CSS class names.
 *
 * This function works in tandem with @see goog.setCssNameMapping.
 *
 * Without any mapping set, the arguments are simple joined with a hyphen and
 * passed through unaltered.
 *
 * When there is a mapping, there are two possible styles in which these
 * mappings are used. In the BY_PART style, each part (i.e. in between hyphens)
 * of the passed in css name is rewritten according to the map. In the BY_WHOLE
 * style, the full css name is looked up in the map directly. If a rewrite is
 * not specified by the map, the compiler will output a warning.
 *
 * When the mapping is passed to the compiler, it will replace calls to
 * goog.getCssName with the strings from the mapping, e.g.
 *     var x = goog.getCssName('foo');
 *     var y = goog.getCssName(this.baseClass, 'active');
 *  becomes:
 *     var x = 'foo';
 *     var y = this.baseClass + '-active';
 *
 * If one argument is passed it will be processed, if two are passed only the
 * modifier will be processed, as it is assumed the first argument was generated
 * as a result of calling goog.getCssName.
 *
 * @param {string} className The class name.
 * @param {string=} opt_modifier A modifier to be appended to the class name.
 * @return {string} The class name or the concatenation of the class name and
 *     the modifier.
 */
goog.getCssName = function(className, opt_modifier) {
  // String() is used for compatibility with compiled soy where the passed
  // className can be non-string objects.
  if (String(className).charAt(0) == '.') {
    throw new Error(
        'className passed in goog.getCssName must not start with ".".' +
        ' You passed: ' + className);
  }

  var getMapping = function(cssName) {
    return goog.cssNameMapping_[cssName] || cssName;
  };

  var renameByParts = function(cssName) {
    // Remap all the parts individually.
    var parts = cssName.split('-');
    var mapped = [];
    for (var i = 0; i < parts.length; i++) {
      mapped.push(getMapping(parts[i]));
    }
    return mapped.join('-');
  };

  var rename;
  if (goog.cssNameMapping_) {
    rename =
        goog.cssNameMappingStyle_ == 'BY_WHOLE' ? getMapping : renameByParts;
  } else {
    rename = function(a) {
      return a;
    };
  }

  var result =
      opt_modifier ? className + '-' + rename(opt_modifier) : rename(className);

  // The special CLOSURE_CSS_NAME_MAP_FN allows users to specify further
  // processing of the class name.
  if (goog.global.CLOSURE_CSS_NAME_MAP_FN) {
    return goog.global.CLOSURE_CSS_NAME_MAP_FN(result);
  }

  return result;
};


/**
 * Sets the map to check when returning a value from goog.getCssName(). Example:
 * <pre>
 * goog.setCssNameMapping({
 *   "goog": "a",
 *   "disabled": "b",
 * });
 *
 * var x = goog.getCssName('goog');
 * // The following evaluates to: "a a-b".
 * goog.getCssName('goog') + ' ' + goog.getCssName(x, 'disabled')
 * </pre>
 * When declared as a map of string literals to string literals, the JSCompiler
 * will replace all calls to goog.getCssName() using the supplied map if the
 * --process_closure_primitives flag is set.
 *
 * @param {!Object} mapping A map of strings to strings where keys are possible
 *     arguments to goog.getCssName() and values are the corresponding values
 *     that should be returned.
 * @param {string=} opt_style The style of css name mapping. There are two valid
 *     options: 'BY_PART', and 'BY_WHOLE'.
 * @see goog.getCssName for a description.
 */
goog.setCssNameMapping = function(mapping, opt_style) {
  goog.cssNameMapping_ = mapping;
  goog.cssNameMappingStyle_ = opt_style;
};


/**
 * To use CSS renaming in compiled mode, one of the input files should have a
 * call to goog.setCssNameMapping() with an object literal that the JSCompiler
 * can extract and use to replace all calls to goog.getCssName(). In uncompiled
 * mode, JavaScript code should be loaded before this base.js file that declares
 * a global variable, CLOSURE_CSS_NAME_MAPPING, which is used below. This is
 * to ensure that the mapping is loaded before any calls to goog.getCssName()
 * are made in uncompiled mode.
 *
 * A hook for overriding the CSS name mapping.
 * @type {!Object<string, string>|undefined}
 */
goog.global.CLOSURE_CSS_NAME_MAPPING;


if (!COMPILED && goog.global.CLOSURE_CSS_NAME_MAPPING) {
  // This does not call goog.setCssNameMapping() because the JSCompiler
  // requires that goog.setCssNameMapping() be called with an object literal.
  goog.cssNameMapping_ = goog.global.CLOSURE_CSS_NAME_MAPPING;
}

/**
 * Options bag type for `goog.getMsg()` third argument.
 *
 * It is important to note that these options need to be known at compile time,
 * so they must always be provided to `goog.getMsg()` as an actual object
 * literal in the function call. Otherwise, closure-compiler will report an
 * error.
 * @record
 */
goog.GetMsgOptions = function() {};

/**
 * If `true`, escape '<' in the message string to '&lt;'.
 *
 * Used by Closure Templates where the generated code size and performance is
 * critical which is why {@link goog.html.SafeHtmlFormatter} is not used.
 * The value must be literal `true` or `false`.
 * @type {boolean|undefined}
 */
goog.GetMsgOptions.prototype.html;

/**
 * If `true`, unescape common html entities: &gt;, &lt;, &apos;, &quot; and
 * &amp;.
 *
 * Used for messages not in HTML context, such as with the `textContent`
 * property.
 * The value must be literal `true` or `false`.
 * @type {boolean|undefined}
 */
goog.GetMsgOptions.prototype.unescapeHtmlEntities;

/**
 * Associates placeholder names with strings showing how their values are
 * obtained.
 *
 * This field is intended for use in automatically generated JS code.
 * Human-written code should use meaningful placeholder names instead.
 *
 * closure-compiler uses this as the contents of the `<ph>` tag in the
 * XMB file it generates or defaults to `-` for historical reasons.
 *
 * Must be an object literal.
 * Ignored at runtime.
 * Keys are placeholder names.
 * Values are string literals indicating how the value is obtained.
 * Typically this is a snippet of source code.
 * @type {!Object<string, string>|undefined}
 */
goog.GetMsgOptions.prototype.original_code;

/**
 * Associates placeholder names with example values.
 *
 * closure-compiler uses this as the contents of the `<ex>` tag in the
 * XMB file it generates or defaults to `-` for historical reasons.
 *
 * Must be an object literal.
 * Ignored at runtime.
 * Keys are placeholder names.
 * Values are string literals containing example placeholder values.
 * (e.g. "George McFly" for a name placeholder)
 * @type {!Object<string, string>|undefined}
 */
goog.GetMsgOptions.prototype.example;

/**
 * A hook for providing a custom message retrieval function to
 * augment `goog.getMsg`.
 *
 * If an object is assigned to `CLOSURE_P16N_GET_MSG` in the global scope
 * *before* base.js is loaded, `goog.getMsg` will use the function provided
 * under the key 'goog.getMsg' on this object instead of its default
 * implementation. This allows a "p16n library" to take over the message
 * localization process.
 *
 * The provided object is expected to have the following structure:
 * <pre>
 *   {
 *     'goog.getMsg': function(string, !Object<string, string>=,
 * !goog.GetMsgOptions=): string, 'declareIcuTemplate': function(string, string,
 * !Object<string, string>=, !goog.GetMsgOptions=): string
 *   }
 * </pre>
 *
 * Example:
 * <pre>
 *   // In a script loaded *before* base.js:
 *   window.CLOSURE_P16N_GET_MSG = {
 *     'goog.getMsg': function(str, opt_values, opt_options) {
 *       // Custom logic to fetch and format the message from a p16n system.
 *       // 'str' is the original message string.
 *       // 'opt_values' is the placeholder map.
 *       // 'opt_options' are options like html/unescapeHtmlEntities.
 *       return p16nLibrary.getLocalizedMessage(str, opt_values, opt_options);
 *     },
 *     'declareIcuTemplate': function(templateString, name, opt_values,
 * opt_options) {
 *       // Custom logic to declare an ICU template.
 *       return p16nLibrary.declareIcuTemplate(templateString, name, opt_values,
 * opt_options);
 *     }
 *   };
 * </pre>
 *
 *
 * @type {({
 *   'goog.getMsg': (function(string, !Object<string, string>=,
 * !goog.GetMsgOptions=): string), 'declareIcuTemplate': (function(string,
 * string, !Object<string, string>=, !goog.GetMsgOptions=): string)
 * }|undefined)}
 */
goog.global.CLOSURE_P16N_GET_MSG;

/**
 * @define {boolean} Whether to use the global CLOSURE_P16N_GET_MSG override for
 * goog.getMsg.
 */
goog.USE_GET_MSG_OVERRIDE = goog.define('goog.USE_GET_MSG_OVERRIDE', false);

/**
 * Gets a localized message.
 *
 * This function is a compiler primitive. If you give the compiler a localized
 * message bundle, it will replace the string at compile-time with a localized
 * version, and expand goog.getMsg call to a concatenated string.
 *
 * Messages must be initialized in the form:
 * <code>
 * var MSG_NAME = goog.getMsg('Hello {$placeholder}', {'placeholder': 'world'});
 * </code>
 *
 * This function produces a string which should be treated as plain text. Use
 * {@link goog.html.SafeHtmlFormatter} in conjunction with goog.getMsg to
 * produce SafeHtml.
 *
 * @param {string} str Translatable string, places holders in the form {$foo}.
 * @param {!Object<string, string>=} opt_values Maps place holder name to value.
 * @param {!goog.GetMsgOptions=} opt_options see `goog.GetMsgOptions`
 * @return {string} message with placeholders filled.
 */
goog.getMsg = function(str, opt_values, opt_options) {
  if (goog.USE_GET_MSG_OVERRIDE && !COMPILED) {
    if (goog.global.CLOSURE_P16N_GET_MSG &&
        goog.global.CLOSURE_P16N_GET_MSG['goog.getMsg'] != undefined) {
      str = goog.global.CLOSURE_P16N_GET_MSG['goog.getMsg'](
          str, opt_values, opt_options);
    } else {
      throw new Error('Closure p16n getMsg override is not available.');
    }
  }
  if (opt_options && opt_options.html) {
    // Note that '&' is not replaced because the translation can contain HTML
    // entities.
    str = str.replace(/</g, '&lt;');
  }
  if (opt_options && opt_options.unescapeHtmlEntities) {
    // Note that "&amp;" must be the last to avoid "creating" new entities.
    str = str.replace(/&lt;/g, '<')
              .replace(/&gt;/g, '>')
              .replace(/&apos;/g, '\'')
              .replace(/&quot;/g, '"')
              .replace(/&amp;/g, '&');
  }
  if (opt_values) {
    str = str.replace(/\{\$([^}]+)}/g, function(match, key) {
      return (opt_values != null && key in opt_values) ? opt_values[key] :
                                                         match;
    });
  }
  return str;
};


/**
 * Gets a localized message. If the message does not have a translation, gives a
 * fallback message.
 *
 * This is useful when introducing a new message that has not yet been
 * translated into all languages.
 *
 * This function is a compiler primitive. Must be used in the form:
 * <code>var x = goog.getMsgWithFallback(MSG_A, MSG_B);</code>
 * where MSG_A and MSG_B were initialized with goog.getMsg.
 *
 * @param {string} a The preferred message.
 * @param {string} b The fallback message.
 * @return {string} The best translated message.
 */
goog.getMsgWithFallback = function(a, b) {
  return a;
};


/**
 * Exposes an unobfuscated global namespace path for the given object.
 * Note that fields of the exported object *will* be obfuscated, unless they are
 * exported in turn via this function or goog.exportProperty.
 *
 * Also handy for making public items that are defined in anonymous closures.
 *
 * ex. goog.exportSymbol('public.path.Foo', Foo);
 *
 * ex. goog.exportSymbol('public.path.Foo.staticFunction', Foo.staticFunction);
 *     public.path.Foo.staticFunction();
 *
 * ex. goog.exportSymbol('public.path.Foo.prototype.myMethod',
 *                       Foo.prototype.myMethod);
 *     new public.path.Foo().myMethod();
 *
 * @param {string} publicPath Unobfuscated name to export.
 * @param {*} object Object the name should point to.
 * @param {?Object=} objectToExportTo The object to add the path to; default
 *     is goog.global.
 */
goog.exportSymbol = function(publicPath, object, objectToExportTo) {
  goog.exportPath_(
      publicPath, object, /* overwriteImplicit= */ true, objectToExportTo);
};


/**
 * Exports a property unobfuscated into the object's namespace.
 * ex. goog.exportProperty(Foo, 'staticFunction', Foo.staticFunction);
 * ex. goog.exportProperty(Foo.prototype, 'myMethod', Foo.prototype.myMethod);
 * @param {Object} object Object whose static property is being exported.
 * @param {string} publicName Unobfuscated name to export.
 * @param {*} symbol Object the name should point to.
 */
goog.exportProperty = function(object, publicName, symbol) {
  object[publicName] = symbol;
};


/**
 * Returns the value of a given name, or undefined if there are no other
 * references to the name.
 *
 * This function is evaluated statically, at compile time, as long as the
 * appropriate compiler passes are enabled.  If these compiler passes are not
 * enabled, the function is a no-op, and will just return its argument
 * unmodified.
 *
 * Usage:
 * <pre>
 * // If there are other references to `x`, `xOrUndefined` will be `x`.
 * // Otherwise, `xOrUndefined` will be `undefined`.
 * var xOrUndefined = goog.weakUsage(x);
 * </pre>
 *
 * It is an error to call `goog.weakUsage` with an argument that is not a name.
 *
 * @param {T} name A symbol name to reference weakly.
 * @return {T|undefined} The object or undefined.
 * @template T
 * @noinline
 */
goog.weakUsage = function(name) {
  return name;
};


/**
 * Inherit the prototype methods from one constructor into another.
 *
 * Usage:
 * <pre>
 * function ParentClass(a, b) { }
 * ParentClass.prototype.foo = function(a) { };
 *
 * function ChildClass(a, b, c) {
 *   ChildClass.base(this, 'constructor', a, b);
 * }
 * goog.inherits(ChildClass, ParentClass);
 *
 * var child = new ChildClass('a', 'b', 'see');
 * child.foo(); // This works.
 * </pre>
 *
 * @param {!Function} childCtor Child class.
 * @param {!Function} parentCtor Parent class.
 * @suppress {strictMissingProperties} superClass_ and base is not defined on
 *    Function.
 * @deprecated Use ECMAScript class syntax instead.
 */
goog.inherits = function(childCtor, parentCtor) {
  /** @constructor */
  function tempCtor() {}
  tempCtor.prototype = parentCtor.prototype;
  childCtor.superClass_ = parentCtor.prototype;
  childCtor.prototype = new tempCtor();
  /** @override */
  childCtor.prototype.constructor = childCtor;

  /**
   * Calls superclass constructor/method.
   *
   * This function is only available if you use goog.inherits to
   * express inheritance relationships between classes.
   *
   * NOTE: This is a replacement for goog.base and for superClass_
   * property defined in childCtor.
   *
   * @param {!Object} me Should always be "this".
   * @param {string} methodName The method name to call. Calling
   *     superclass constructor can be done with the special string
   *     'constructor'.
   * @param {...*} var_args The arguments to pass to superclass
   *     method/constructor.
   * @return {*} The return value of the superclass method/constructor.
   */
  childCtor.base = function(me, methodName, var_args) {
    // Copying using loop to avoid deop due to passing arguments object to
    // function. This is faster in many JS engines as of late 2014.
    var args = new Array(arguments.length - 2);
    for (var i = 2; i < arguments.length; i++) {
      args[i - 2] = arguments[i];
    }
    return parentCtor.prototype[methodName].apply(me, args);
  };
};


/**
 * Allow for aliasing within scope functions.  This function exists for
 * uncompiled code - in compiled code the calls will be inlined and the aliases
 * applied.  In uncompiled code the function is simply run since the aliases as
 * written are valid JavaScript.
 *
 * MOE:begin_intracomment_strip
 * See the goog.scope document at http://go/goog.scope
 *
 * For more on goog.scope deprecation, see the style guide entry:
 * http://go/jsstyle#appendices-legacy-exceptions-goog-scope
 * MOE:end_intracomment_strip
 *
 * @param {function()} fn Function to call.  This function can contain aliases
 *     to namespaces (e.g. "var dom = goog.dom") or classes
 *     (e.g. "var Timer = goog.Timer").
 * @deprecated Use goog.module instead.
 */
goog.scope = function(fn) {
  if (goog.isInModuleLoader_()) {
    throw new Error('goog.scope is not supported within a module.');
  }
  fn.call(goog.global);
};


/*
 * To support uncompiled, strict mode bundles that use eval to divide source
 * like so:
 *    eval('someSource;//# sourceUrl sourcefile.js');
 * We need to export the globally defined symbols "goog" and "COMPILED".
 * Exporting "goog" breaks the compiler optimizations, so we required that
 * be defined externally.
 * NOTE: We don't use goog.exportSymbol here because we don't want to trigger
 * extern generation when that compiler option is enabled.
 */
if (!COMPILED) {
  goog.LEGACY_NAMESPACE_OBJECT_['COMPILED'] = COMPILED;
}

/**
 * Returns the parameter.
 * @param {string} s
 * @return {string}
 * @private
 */
goog.identity_ = function(s) {
  return s;
};


/**
 * Creates Trusted Types policy if Trusted Types are supported by the browser.
 * The policy just blesses any string as a Trusted Type. It is not visibility
 * restricted because anyone can also call trustedTypes.createPolicy directly.
 * However, the allowed names should be restricted by a HTTP header and the
 * reference to the created policy should be visibility restricted.
 * @param {string} name
 * @return {?TrustedTypePolicy}
 */
goog.createTrustedTypesPolicy = function(name) {
  var policy = null;
  var policyFactory = goog.global.trustedTypes;
  if (!policyFactory || !policyFactory.createPolicy) {
    return policy;
  }
  // trustedTypes.createPolicy throws if called with a name that is already
  // registered, even in report-only mode. Until the API changes, catch the
  // error not to break the applications functionally. In such case, the code
  // will fall back to using regular Safe Types.
  // TODO: Remove catching once createPolicy API stops throwing.
  try {
    policy = policyFactory.createPolicy(name, {
      createHTML: goog.identity_,
      createScript: goog.identity_,
      createScriptURL: goog.identity_
    });
  } catch (e) {
    goog.logToConsole_(e.message);
  }
  return policy;
};

// There's a bug in the compiler where without collapse properties the
// Closure namespace defines do not guard code correctly. To help reduce code
// size also check for !COMPILED even though it redundant until this is fixed.
if (!COMPILED && goog.DEPENDENCIES_ENABLED) {
  // MOE:begin_strip
  // TODO This object is obsolete but some people are relying on
  // it internally. Keep it around until we migrate them.
  /**
   * @private
   * @type {{
   *   loadFlags: !Object<string, !Object<string, string>>,
   *   nameToPath: !Object<string, string>,
   *   requires: !Object<string, !Object<string, boolean>>,
   *   visited: !Object<string, boolean>,
   *   written: !Object<string, boolean>,
   *   deferred: !Object<string, string>
   * }}
   */
  goog.dependencies_ = {
    loadFlags: {},  // 1 to 1

    nameToPath: {},  // 1 to 1

    requires: {},  // 1 to many

    // Used when resolving dependencies to prevent us from visiting file
    // twice.
    visited: {},

    written: {},  // Used to keep track of script files we have written.

    deferred: {}  // Used to track deferred module evaluations in old IEs
  };

  /**
   * @return {!Object}
   * @private
   */
  goog.getLoader_ = function() {
    return {
      dependencies_: goog.dependencies_,
      writeScriptTag_: goog.writeScriptTag_
    };
  };


  /**
   * @param {string} src The script url.
   * @param {string=} opt_sourceText The optionally source text to evaluate
   * @return {boolean} True if the script was imported, false otherwise.
   * @private
   */
  goog.writeScriptTag_ = function(src, opt_sourceText) {
    if (goog.inHtmlDocument_()) {
      /** @type {!HTMLDocument} */
      var doc = goog.global.document;

      // If the user tries to require a new symbol after document load,
      // something has gone terribly wrong. Doing a document.write would
      // wipe out the page. This does not apply to the CSP-compliant method
      // of writing script tags.
      if (!goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING &&
          doc.readyState == 'complete') {
        // Certain test frameworks load base.js multiple times, which tries
        // to write deps.js each time. If that happens, just fail silently.
        // These frameworks wipe the page between each load of base.js, so this
        // is OK.
        var isDeps = /\bdeps.js$/.test(src);
        if (isDeps) {
          return false;
        } else {
          throw Error('Cannot write "' + src + '" after document load');
        }
      }

      var nonceAttr = '';
      var nonce = goog.getScriptNonce_();
      if (nonce) {
        nonceAttr = ' nonce="' + nonce + '"';
      }

      if (opt_sourceText === undefined) {
        var script = '<script src="' + src + '"' + nonceAttr + '></' +
            'script>';
        doc.write(
            goog.TRUSTED_TYPES_POLICY_ ?
                goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
                script);
      } else {
        var script = '<script' + nonceAttr + '>' +
            goog.protectScriptTag_(opt_sourceText) + '</' +
            'script>';
        doc.write(
            goog.TRUSTED_TYPES_POLICY_ ?
                goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
                script);
      }
      return true;
    } else {
      return false;
    }
  };
  // MOE:end_strip


  /**
   * Tries to detect whether is in the context of an HTML document.
   * @return {boolean} True if it looks like HTML document.
   * @private
   */
  goog.inHtmlDocument_ = function() {
    /** @type {!Document} */
    var doc = goog.global.document;
    return doc != null && 'write' in doc;  // XULDocument misses write.
  };


  /**
   * We'd like to check for if the document readyState is 'loading'; however
   * there are bugs on IE 10 and below where the readyState being anything other
   * than 'complete' is not reliable.
   * @return {boolean}
   * @private
   */
  goog.isDocumentLoading_ = function() {
    // attachEvent is available on IE 6 thru 10 only, and thus can be used to
    // detect those browsers.
    /** @type {!HTMLDocument} */
    var doc = goog.global.document;
    return doc.attachEvent ? doc.readyState != 'complete' :
                             doc.readyState == 'loading';
  };


  /**
   * Tries to detect the base path of base.js script that bootstraps Closure.
   * @private
   */
  goog.findBasePath_ = function() {
    if (goog.global.CLOSURE_BASE_PATH != undefined &&
        // Anti DOM-clobbering runtime check (b/37736576).
        typeof goog.global.CLOSURE_BASE_PATH === 'string') {
      goog.basePath = goog.global.CLOSURE_BASE_PATH;
      return;
    } else if (!goog.inHtmlDocument_()) {
      return;
    }
    /** @type {!Document} */
    var doc = goog.global.document;
    // If we have a currentScript available, use it exclusively.
    var currentScript = doc.currentScript;
    if (currentScript) {
      var scripts = [currentScript];
    } else {
      var scripts = doc.getElementsByTagName('SCRIPT');
    }
    // Search backwards since the current script is in almost all cases the one
    // that has base.js.
    for (var i = scripts.length - 1; i >= 0; --i) {
      var script = /** @type {!HTMLScriptElement} */ (scripts[i]);
      var src = script.src;
      var qmark = src.lastIndexOf('?');
      var l = qmark == -1 ? src.length : qmark;
      if (src.slice(l - 7, l) == 'base.js') {
        goog.basePath = src.slice(0, l - 7);
        return;
      }
    }
  };

  goog.findBasePath_();

  /**
   * Rewrites closing script tags in input to avoid ending an enclosing script
   * tag.
   *
   * @param {string} str
   * @return {string}
   * @private
   */
  goog.protectScriptTag_ = function(str) {
    return str.replace(/<\/(SCRIPT)/ig, '\\x3c/$1');
  };


  /**
   * A debug loader is responsible for downloading and executing javascript
   * files in an unbundled, uncompiled environment.
   *
   * This can be custimized via the setDependencyFactory method, or by
   * CLOSURE_IMPORT_SCRIPT/CLOSURE_LOAD_FILE_SYNC.
   *
   * @struct @constructor @final @private
   */
  goog.DebugLoader_ = function() {
    /** @private @const {!Object<string, !goog.Dependency>} */
    this.dependencies_ = {};
    /** @private @const {!Object<string, string>} */
    this.idToPath_ = {};
    /** @private @const {!Object<string, boolean>} */
    this.written_ = {};
    /** @private @const {!Array<!goog.Dependency>} */
    this.loadingDeps_ = [];
    /** @private {!Array<!goog.Dependency>} */
    this.depsToLoad_ = [];
    /** @private {boolean} */
    this.paused_ = false;
    /** @private {!goog.DependencyFactory} */
    this.factory_ = new goog.DependencyFactory();
    /** @private @const {!Object<string, !Function>} */
    this.deferredCallbacks_ = {};
    /** @private @const {!Array<string>} */
    this.deferredQueue_ = [];
  };


  /**
   * Loads the Closure deps.js file.
   *
   * Exposed a function so after base is loaded, and
   * then this can be called to load the closure deps.js file.
   */
  goog.DebugLoader_.prototype.loadClosureDeps = function() {
    // Circumvent addDependency, which would try to transpile deps.js if
    // transpile is set to always.
    var relPath = 'deps.js';
    this.depsToLoad_.push(this.factory_.createDependency(
        goog.normalizePath_(goog.basePath + relPath), relPath, [], [], {}));
    this.loadDeps_();
  };


  /**
   * Notifies the debug loader when a dependency has been requested.
   *
   * @param {string} absPathOrId Path of the dependency or goog id.
   * @param {boolean=} opt_force
   */
  goog.DebugLoader_.prototype.requested = function(absPathOrId, opt_force) {
    var path = this.getPathFromDeps_(absPathOrId);
    if (path &&
        (opt_force || this.areDepsLoaded_(this.dependencies_[path].requires))) {
      var callback = this.deferredCallbacks_[path];
      if (callback) {
        delete this.deferredCallbacks_[path];
        callback();
      }
    }
  };


  /**
   * Sets the dependency factory, which can be used to create custom
   * goog.Dependency implementations to control how dependencies are loaded.
   *
   * @param {!goog.DependencyFactory} factory
   */
  goog.DebugLoader_.prototype.setDependencyFactory = function(factory) {
    this.factory_ = factory;
  };


  /**
   * Travserses the dependency graph and queues the given dependency, and all of
   * its transitive dependencies, for loading and then starts loading if not
   * paused.
   *
   * @param {string} namespace
   * @private
   */
  goog.DebugLoader_.prototype.load_ = function(namespace) {
    if (!this.getPathFromDeps_(namespace)) {
      var errorMessage = 'goog.require could not find: ' + namespace;
      goog.logToConsole_(errorMessage);
    } else {
      var loader = this;

      var deps = [];

      /** @param {string} namespace */
      var visit = function(namespace) {
        var path = loader.getPathFromDeps_(namespace);

        if (!path) {
          throw new Error('Bad dependency path or symbol: ' + namespace);
        }

        if (loader.written_[path]) {
          return;
        }

        loader.written_[path] = true;

        var dep = loader.dependencies_[path];
        // MOE:begin_strip
        if (goog.dependencies_.written[dep.relativePath]) {
          return;
        }
        // MOE:end_strip
        for (var i = 0; i < dep.requires.length; i++) {
          if (!goog.isProvided_(dep.requires[i])) {
            visit(dep.requires[i]);
          }
        }

        deps.push(dep);
      };

      visit(namespace);

      var wasLoading = !!this.depsToLoad_.length;
      this.depsToLoad_ = this.depsToLoad_.concat(deps);

      if (!this.paused_ && !wasLoading) {
        this.loadDeps_();
      }
    }
  };


  /**
   * Loads any queued dependencies until they are all loaded or paused.
   *
   * @private
   */
  goog.DebugLoader_.prototype.loadDeps_ = function() {
    var loader = this;
    var paused = this.paused_;

    while (this.depsToLoad_.length && !paused) {
      (function() {
        var loadCallDone = false;
        var dep = loader.depsToLoad_.shift();

        var loaded = false;
        loader.loading_(dep);

        var controller = {
          pause: function() {
            if (loadCallDone) {
              throw new Error('Cannot call pause after the call to load.');
            } else {
              paused = true;
            }
          },
          resume: function() {
            if (loadCallDone) {
              loader.resume_();
            } else {
              // Some dep called pause and then resume in the same load call.
              // Just keep running this same loop.
              paused = false;
            }
          },
          loaded: function() {
            if (loaded) {
              throw new Error('Double call to loaded.');
            }

            loaded = true;
            loader.loaded_(dep);
          },
          pending: function() {
            // Defensive copy.
            var pending = [];
            for (var i = 0; i < loader.loadingDeps_.length; i++) {
              pending.push(loader.loadingDeps_[i]);
            }
            return pending;
          },
          /**
           * @param {goog.ModuleType} type
           */
          setModuleState: function(type) {
            goog.moduleLoaderState_ = {
              type: type,
              moduleName: '',
              declareLegacyNamespace: false,
              preventModuleExportSealing: false,
            };
          },
          /** @type {function(string, string, string=)} */
          registerEs6ModuleExports: function(
              path, exports, opt_closureNamespace) {
            if (opt_closureNamespace) {
              goog.loadedModules_[opt_closureNamespace] = {
                exports: exports,
                type: goog.ModuleType.ES6,
                moduleId: opt_closureNamespace || ''
              };
            }
          },
          /** @type {function(string, ?)} */
          registerGoogModuleExports: function(moduleId, exports) {
            goog.loadedModules_[moduleId] = {
              exports: exports,
              type: goog.ModuleType.GOOG,
              moduleId: moduleId
            };
          },
          clearModuleState: function() {
            goog.moduleLoaderState_ = null;
          },
          defer: function(callback) {
            if (loadCallDone) {
              throw new Error(
                  'Cannot register with defer after the call to load.');
            }
            loader.defer_(dep, callback);
          },
          areDepsLoaded: function() {
            return loader.areDepsLoaded_(dep.requires);
          }
        };

        try {
          dep.load(controller);
        } finally {
          loadCallDone = true;
        }
      })();
    }

    if (paused) {
      this.pause_();
    }
  };


  /** @private */
  goog.DebugLoader_.prototype.pause_ = function() {
    this.paused_ = true;
  };


  /** @private */
  goog.DebugLoader_.prototype.resume_ = function() {
    if (this.paused_) {
      this.paused_ = false;
      this.loadDeps_();
    }
  };


  /**
   * Marks the given dependency as loading (load has been called but it has not
   * yet marked itself as finished). Useful for dependencies that want to know
   * what else is loading. Example: goog.modules cannot eval if there are
   * loading dependencies.
   *
   * @param {!goog.Dependency} dep
   * @private
   */
  goog.DebugLoader_.prototype.loading_ = function(dep) {
    this.loadingDeps_.push(dep);
  };


  /**
   * Marks the given dependency as having finished loading and being available
   * for require.
   *
   * @param {!goog.Dependency} dep
   * @private
   */
  goog.DebugLoader_.prototype.loaded_ = function(dep) {
    for (var i = 0; i < this.loadingDeps_.length; i++) {
      if (this.loadingDeps_[i] == dep) {
        this.loadingDeps_.splice(i, 1);
        break;
      }
    }

    for (var i = 0; i < this.deferredQueue_.length; i++) {
      if (this.deferredQueue_[i] == dep.path) {
        this.deferredQueue_.splice(i, 1);
        break;
      }
    }

    if (this.loadingDeps_.length == this.deferredQueue_.length &&
        !this.depsToLoad_.length) {
      // Something has asked to load these, but they may not be directly
      // required again later, so load them now that we know we're done loading
      // everything else. e.g. a goog module entry point.
      while (this.deferredQueue_.length) {
        this.requested(this.deferredQueue_.shift(), true);
      }
    }

    dep.loaded();
  };


  /**
   * @param {!Array<string>} pathsOrIds
   * @return {boolean}
   * @private
   */
  goog.DebugLoader_.prototype.areDepsLoaded_ = function(pathsOrIds) {
    for (var i = 0; i < pathsOrIds.length; i++) {
      var path = this.getPathFromDeps_(pathsOrIds[i]);
      if (!path ||
          (!(path in this.deferredCallbacks_) &&
           !goog.isProvided_(pathsOrIds[i]))) {
        return false;
      }
    }

    return true;
  };


  /**
   * @param {string} absPathOrId
   * @return {?string}
   * @private
   */
  goog.DebugLoader_.prototype.getPathFromDeps_ = function(absPathOrId) {
    if (absPathOrId in this.idToPath_) {
      return this.idToPath_[absPathOrId];
    } else if (absPathOrId in this.dependencies_) {
      return absPathOrId;
    } else {
      return null;
    }
  };


  /**
   * @param {!goog.Dependency} dependency
   * @param {!Function} callback
   * @private
   */
  goog.DebugLoader_.prototype.defer_ = function(dependency, callback) {
    this.deferredCallbacks_[dependency.path] = callback;
    this.deferredQueue_.push(dependency.path);
  };


  /**
   * Interface for goog.Dependency implementations to have some control over
   * loading of dependencies.
   *
   * @record
   */
  goog.LoadController = function() {};


  /**
   * Tells the controller to halt loading of more dependencies.
   */
  goog.LoadController.prototype.pause = function() {};


  /**
   * Tells the controller to resume loading of more dependencies if paused.
   */
  goog.LoadController.prototype.resume = function() {};


  /**
   * Tells the controller that this dependency has finished loading.
   *
   * This causes this to be removed from pending() and any load callbacks to
   * fire.
   */
  goog.LoadController.prototype.loaded = function() {};


  /**
   * List of dependencies on which load has been called but which have not
   * called loaded on their controller. This includes the current dependency.
   *
   * @return {!Array<!goog.Dependency>}
   */
  goog.LoadController.prototype.pending = function() {};


  /**
   * Registers an object as an ES6 module's exports so that goog.modules may
   * require it by path.
   *
   * @param {string} path Full path of the module.
   * @param {?} exports
   * @param {string=} opt_closureNamespace Closure namespace to associate with
   *     this module.
   */
  goog.LoadController.prototype.registerEs6ModuleExports = function(
      path, exports, opt_closureNamespace) {};


  /**
   * Sets the current module state.
   *
   * @param {goog.ModuleType} type Type of module.
   */
  goog.LoadController.prototype.setModuleState = function(type) {};


  /**
   * Clears the current module state.
   */
  goog.LoadController.prototype.clearModuleState = function() {};


  /**
   * Registers a callback to call once the dependency is actually requested
   * via goog.require + all of the immediate dependencies have been loaded or
   * all other files have been loaded. Allows for lazy loading until
   * require'd without pausing dependency loading, which is needed on old IE.
   *
   * @param {!Function} callback
   */
  goog.LoadController.prototype.defer = function(callback) {};


  /**
   * @return {boolean}
   */
  goog.LoadController.prototype.areDepsLoaded = function() {};


  /**
   * Basic super class for all dependencies Closure Library can load.
   *
   * This default implementation is designed to load untranspiled, non-module
   * scripts in a web broswer.
   *
   * For goog.modules see {@see goog.GoogModuleDependency}.
   * For untranspiled ES6 modules {@see goog.Es6ModuleDependency}.
   *
   * @param {string} path Absolute path of this script.
   * @param {string} relativePath Path of this script relative to goog.basePath.
   * @param {!Array<string>} provides goog.provided or goog.module symbols
   *     in this file.
   * @param {!Array<string>} requires goog symbols or relative paths to Closure
   *     this depends on.
   * @param {!Object<string, string>} loadFlags
   * @struct @constructor
   */
  goog.Dependency = function(
      path, relativePath, provides, requires, loadFlags) {
    /** @const */
    this.path = path;
    /** @const */
    this.relativePath = relativePath;
    /** @const */
    this.provides = provides;
    /** @const */
    this.requires = requires;
    /** @const */
    this.loadFlags = loadFlags;
    /** @private {boolean} */
    this.loaded_ = false;
    /** @private {!Array<function()>} */
    this.loadCallbacks_ = [];
  };


  /**
   * @return {string} The pathname part of this dependency's path if it is a
   *     URI.
   */
  goog.Dependency.prototype.getPathName = function() {
    var pathName = this.path;
    var protocolIndex = pathName.indexOf('://');
    if (protocolIndex >= 0) {
      pathName = pathName.substring(protocolIndex + 3);
      var slashIndex = pathName.indexOf('/');
      if (slashIndex >= 0) {
        pathName = pathName.substring(slashIndex + 1);
      }
    }
    return pathName;
  };


  /**
   * @param {function()} callback Callback to fire as soon as this has loaded.
   * @final
   */
  goog.Dependency.prototype.onLoad = function(callback) {
    if (this.loaded_) {
      callback();
    } else {
      this.loadCallbacks_.push(callback);
    }
  };


  /**
   * Marks this dependency as loaded and fires any callbacks registered with
   * onLoad.
   * @final
   */
  goog.Dependency.prototype.loaded = function() {
    this.loaded_ = true;
    var callbacks = this.loadCallbacks_;
    this.loadCallbacks_ = [];
    for (var i = 0; i < callbacks.length; i++) {
      callbacks[i]();
    }
  };


  /**
   * Whether or not document.written / appended script tags should be deferred.
   *
   * @private {boolean}
   */
  goog.Dependency.defer_ = false;


  /**
   * Map of script ready / state change callbacks. Old IE cannot handle putting
   * these properties on goog.global.
   *
   * @private @const {!Object<string, function(?):undefined>}
   */
  goog.Dependency.callbackMap_ = {};


  /**
   * @param {function(...?):?} callback
   * @return {string}
   * @private
   */
  goog.Dependency.registerCallback_ = function(callback) {
    var key = Math.random().toString(32);
    goog.Dependency.callbackMap_[key] = callback;
    return key;
  };


  /**
   * @param {string} key
   * @private
   */
  goog.Dependency.unregisterCallback_ = function(key) {
    delete goog.Dependency.callbackMap_[key];
  };


  /**
   * @param {string} key
   * @param {...?} var_args
   * @private
   */
  goog.Dependency.callback_ = function(key, var_args) {
    if (key in goog.Dependency.callbackMap_) {
      var callback = goog.Dependency.callbackMap_[key];
      var args = [];
      for (var i = 1; i < arguments.length; i++) {
        args.push(arguments[i]);
      }
      callback.apply(undefined, args);
    } else {
      var errorMessage = 'Callback key ' + key +
          ' does not exist (was base.js loaded more than once?).';
      // MOE:begin_strip
      // TODO: Some people internally are mistakenly loading
      // base.js twice, and this can happen while a dependency is loading,
      // wiping out state.
      goog.logToConsole_(errorMessage);
      // MOE:end_strip
      // MOE:insert throw Error(errorMessage);
    }
  };


  /**
   * Starts loading this dependency. This dependency can pause loading if it
   * needs to and resume it later via the controller interface.
   *
   * When this is loaded it should call controller.loaded(). Note that this will
   * end up calling the loaded method of this dependency; there is no need to
   * call it explicitly.
   *
   * @param {!goog.LoadController} controller
   */
  goog.Dependency.prototype.load = function(controller) {
    if (goog.global.CLOSURE_IMPORT_SCRIPT) {
      if (goog.global.CLOSURE_IMPORT_SCRIPT(this.path)) {
        controller.loaded();
      } else {
        controller.pause();
      }
      return;
    }

    if (!goog.inHtmlDocument_()) {
      goog.logToConsole_(
          'Cannot use default debug loader outside of HTML documents.');
      if (this.relativePath == 'deps.js') {
        // CLOSURE_IMPORT_SCRIPT should be set *before* base.js is loaded.
        goog.logToConsole_(
            'Consider setting CLOSURE_IMPORT_SCRIPT before loading base.js.');
        controller.loaded();
      } else {
        controller.pause();
      }
      return;
    }

    /** @type {!HTMLDocument} */
    var doc = goog.global.document;

    // If the user tries to require a new symbol after document load,
    // something has gone terribly wrong. Doing a document.write would
    // wipe out the page. This does not apply to the CSP-compliant method
    // of writing script tags.
    if (doc.readyState == 'complete' &&
        !goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING) {
      // Certain test frameworks load base.js multiple times, which tries
      // to write deps.js each time. If that happens, just fail silently.
      // These frameworks wipe the page between each load of base.js, so this
      // is OK.
      var isDeps = /\bdeps.js$/.test(this.path);
      if (isDeps) {
        controller.loaded();
        return;
      } else {
        throw Error('Cannot write "' + this.path + '" after document load');
      }
    }

    var nonce = goog.getScriptNonce_();
    if (!goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING &&
        goog.isDocumentLoading_()) {
      var key;
      var callback = function(script) {
        if (script.readyState && script.readyState != 'complete') {
          script.onload = callback;
          return;
        }
        goog.Dependency.unregisterCallback_(key);
        controller.loaded();
      };
      key = goog.Dependency.registerCallback_(callback);

      var defer = goog.Dependency.defer_ ? ' defer' : '';
      var nonceAttr = nonce ? ' nonce="' + nonce + '"' : '';
      var script = '<script src="' + this.path + '"' + nonceAttr + defer +
          ' id="script-' + key + '"><\/script>';

      script += '<script' + nonceAttr + '>';

      if (goog.Dependency.defer_) {
        script += 'document.getElementById(\'script-' + key +
            '\').onload = function() {\n' +
            '  goog.Dependency.callback_(\'' + key + '\', this);\n' +
            '};\n';
      } else {
        script += 'goog.Dependency.callback_(\'' + key +
            '\', document.getElementById(\'script-' + key + '\'));';
      }

      script += '<\/script>';

      doc.write(
          goog.TRUSTED_TYPES_POLICY_ ?
              goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
              script);
    } else {
      var scriptEl =
          /** @type {!HTMLScriptElement} */ (doc.createElement('script'));
      scriptEl.defer = goog.Dependency.defer_;
      scriptEl.async = false;

      // If CSP nonces are used, propagate them to dynamically created scripts.
      // This is necessary to allow nonce-based CSPs without 'strict-dynamic'.
      if (nonce) {
        scriptEl.nonce = nonce;
      }

      scriptEl.onload = function() {
        scriptEl.onload = null;
        controller.loaded();
      };

      scriptEl.src = goog.TRUSTED_TYPES_POLICY_ ?
          goog.TRUSTED_TYPES_POLICY_.createScriptURL(this.path) :
          this.path;
      doc.head.appendChild(scriptEl);
    }
  };


  /**
   * @param {string} path Absolute path of this script.
   * @param {string} relativePath Path of this script relative to goog.basePath.
   * @param {!Array<string>} provides Should be an empty array.
   *     TODO add support for adding closure namespaces to ES6
   *     modules for interop purposes.
   * @param {!Array<string>} requires goog symbols or relative paths to Closure
   *     this depends on.
   * @param {!Object<string, string>} loadFlags
   * @struct @constructor
   * @extends {goog.Dependency}
   */
  goog.Es6ModuleDependency = function(
      path, relativePath, provides, requires, loadFlags) {
    goog.Es6ModuleDependency.base(
        this, 'constructor', path, relativePath, provides, requires, loadFlags);
  };
  goog.inherits(goog.Es6ModuleDependency, goog.Dependency);


  /**
   * @override
   * @param {!goog.LoadController} controller
   */
  goog.Es6ModuleDependency.prototype.load = function(controller) {
    if (goog.global.CLOSURE_IMPORT_SCRIPT) {
      if (goog.global.CLOSURE_IMPORT_SCRIPT(this.path)) {
        controller.loaded();
      } else {
        controller.pause();
      }
      return;
    }

    if (!goog.inHtmlDocument_()) {
      goog.logToConsole_(
          'Cannot use default debug loader outside of HTML documents.');
      controller.pause();
      return;
    }

    /** @type {!HTMLDocument} */
    var doc = goog.global.document;

    var dep = this;

    // TODO: Does document.writing really speed up anything? Any
    // difference between this and just waiting for interactive mode and then
    // appending?
    function write(src, contents) {
      var nonceAttr = '';
      var nonce = goog.getScriptNonce_();
      if (nonce) {
        nonceAttr = ' nonce="' + nonce + '"';
      }

      if (contents) {
        var script = '<script type="module" crossorigin' + nonceAttr + '>' +
            contents + '</' +
            'script>';
        doc.write(
            goog.TRUSTED_TYPES_POLICY_ ?
                goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
                script);
      } else {
        var script = '<script type="module" crossorigin src="' + src + '"' +
            nonceAttr + '></' +
            'script>';
        doc.write(
            goog.TRUSTED_TYPES_POLICY_ ?
                goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
                script);
      }
    }

    function append(src, contents) {
      var scriptEl =
          /** @type {!HTMLScriptElement} */ (doc.createElement('script'));
      scriptEl.defer = true;
      scriptEl.async = false;
      scriptEl.type = 'module';
      scriptEl.setAttribute('crossorigin', true);

      // If CSP nonces are used, propagate them to dynamically created scripts.
      // This is necessary to allow nonce-based CSPs without 'strict-dynamic'.
      var nonce = goog.getScriptNonce_();
      if (nonce) {
        scriptEl.nonce = nonce;
      }

      if (contents) {
        scriptEl.text = goog.TRUSTED_TYPES_POLICY_ ?
            goog.TRUSTED_TYPES_POLICY_.createScript(contents) :
            contents;
      } else {
        scriptEl.src = goog.TRUSTED_TYPES_POLICY_ ?
            goog.TRUSTED_TYPES_POLICY_.createScriptURL(src) :
            src;
      }

      doc.head.appendChild(scriptEl);
    }

    var create;

    if (goog.isDocumentLoading_()) {
      create = write;
      // We can ONLY call document.write if we are guaranteed that any
      // non-module script tags document.written after this are deferred.
      // Small optimization, in theory document.writing is faster.
      goog.Dependency.defer_ = true;
    } else {
      create = append;
    }

    // Write 4 separate tags here:
    // 1) Sets the module state at the correct time (just before execution).
    // 2) A src node for this, which just hopefully lets the browser load it a
    //    little early (no need to parse #3).
    // 3) Import the module and register it.
    // 4) Clear the module state at the correct time. Guaranteed to run even
    //    if there is an error in the module (#3 will not run if there is an
    //    error in the module).
    var beforeKey = goog.Dependency.registerCallback_(function() {
      goog.Dependency.unregisterCallback_(beforeKey);
      controller.setModuleState(goog.ModuleType.ES6);
    });
    create(undefined, 'goog.Dependency.callback_("' + beforeKey + '")');

    // TODO: Does this really speed up anything?
    create(this.path, undefined);

    var registerKey = goog.Dependency.registerCallback_(function(exports) {
      goog.Dependency.unregisterCallback_(registerKey);
      controller.registerEs6ModuleExports(
          dep.path, exports, goog.moduleLoaderState_.moduleName);
    });
    create(
        undefined,
        'import * as m from "' + this.path + '"; goog.Dependency.callback_("' +
            registerKey + '", m)');

    var afterKey = goog.Dependency.registerCallback_(function() {
      goog.Dependency.unregisterCallback_(afterKey);
      controller.clearModuleState();
      controller.loaded();
    });
    create(undefined, 'goog.Dependency.callback_("' + afterKey + '")');
  };


  /**
   * Superclass of any dependency that needs to be loaded into memory,
   * transformed, and then eval'd (goog.modules and transpiled files).
   *
   * @param {string} path Absolute path of this script.
   * @param {string} relativePath Path of this script relative to goog.basePath.
   * @param {!Array<string>} provides goog.provided or goog.module symbols
   *     in this file.
   * @param {!Array<string>} requires goog symbols or relative paths to Closure
   *     this depends on.
   * @param {!Object<string, string>} loadFlags
   * @struct @constructor @abstract
   * @extends {goog.Dependency}
   */
  goog.TransformedDependency = function(
      path, relativePath, provides, requires, loadFlags) {
    goog.TransformedDependency.base(
        this, 'constructor', path, relativePath, provides, requires, loadFlags);
    /** @private {?string} */
    this.contents_ = null;

    /**
     * Whether to lazily make the synchronous XHR (when goog.require'd) or make
     * the synchronous XHR when initially loading. On FireFox 61 there is a bug
     * where an ES6 module cannot make a synchronous XHR (rather, it can, but if
     * it does then no other ES6 modules will load after).
     *
     * tl;dr we lazy load due to bugs on older browsers and eager load due to
     * bugs on newer ones.
     *
     * https://bugzilla.mozilla.org/show_bug.cgi?id=1477090
     *
     * @private @const {boolean}
     */
    this.lazyFetch_ = !goog.inHtmlDocument_() ||
        !('noModule' in goog.global.document.createElement('script'));
  };
  goog.inherits(goog.TransformedDependency, goog.Dependency);


  /**
   * @override
   * @param {!goog.LoadController} controller
   */
  goog.TransformedDependency.prototype.load = function(controller) {
    var dep = this;

    function fetch() {
      dep.contents_ = goog.loadFileSync_(dep.path);

      if (dep.contents_) {
        dep.contents_ = dep.transform(dep.contents_);
        if (dep.contents_) {
          dep.contents_ += '\n//# sourceURL=' + dep.path;
        }
      }
    }

    if (goog.global.CLOSURE_IMPORT_SCRIPT) {
      fetch();
      if (this.contents_ &&
          goog.global.CLOSURE_IMPORT_SCRIPT('', this.contents_)) {
        this.contents_ = null;
        controller.loaded();
      } else {
        controller.pause();
      }
      return;
    }


    var isEs6 = this.loadFlags['module'] == goog.ModuleType.ES6;

    if (!this.lazyFetch_) {
      fetch();
    }

    function load() {
      if (dep.lazyFetch_) {
        fetch();
      }

      if (!dep.contents_) {
        // loadFileSync_ or transform are responsible. Assume they logged an
        // error.
        return;
      }

      if (isEs6) {
        controller.setModuleState(goog.ModuleType.ES6);
      }

      var namespace;

      try {
        var contents = dep.contents_;
        dep.contents_ = null;
        goog.globalEval(goog.CLOSURE_EVAL_PREFILTER_.createScript(contents));
        if (isEs6) {
          namespace = goog.moduleLoaderState_.moduleName;
        }
      } finally {
        if (isEs6) {
          controller.clearModuleState();
        }
      }

      if (isEs6) {
        // Due to circular dependencies this may not be available for require
        // right now.
        goog.LEGACY_NAMESPACE_OBJECT_['$jscomp']['require']['ensure'](
            [dep.getPathName()], function() {
              controller.registerEs6ModuleExports(
                  dep.path,
                  goog.LEGACY_NAMESPACE_OBJECT_['$jscomp']['require'](
                      dep.getPathName()),
                  namespace);
            });
      }

      controller.loaded();
    }

    // Do not fetch now; in FireFox 47 the synchronous XHR doesn't block all
    // events. If we fetched now and then document.write'd the contents the
    // document.write would be an eval and would execute too soon! Instead write
    // a script tag to fetch and eval synchronously at the correct time.
    function fetchInOwnScriptThenLoad() {
      /** @type {!HTMLDocument} */
      var doc = goog.global.document;

      var key = goog.Dependency.registerCallback_(function() {
        goog.Dependency.unregisterCallback_(key);
        load();
      });

      var nonce = goog.getScriptNonce_();
      var nonceAttr = nonce ? ' nonce="' + nonce + '"' : '';
      var script = '<script' + nonceAttr + '>' +
          goog.protectScriptTag_('goog.Dependency.callback_("' + key + '");') +
          '</' +
          'script>';
      doc.write(
          goog.TRUSTED_TYPES_POLICY_ ?
              goog.TRUSTED_TYPES_POLICY_.createHTML(script) :
              script);
    }

    // If one thing is pending it is this.
    var anythingElsePending = controller.pending().length > 1;

    // Additionally if we are meant to defer scripts but the page is still
    // loading (e.g. an ES6 module is loading) then also defer. Or if we are
    // meant to defer and anything else is pending then defer (those may be
    // scripts that did not need transformation and are just script tags with
    // defer set to true, and we need to evaluate after that deferred script).
    var needsAsyncLoading = goog.Dependency.defer_ &&
        (anythingElsePending || goog.isDocumentLoading_());

    if (needsAsyncLoading) {
      // Note that we only defer when we have to rather than 100% of the time.
      // Always defering would work, but then in theory the order of
      // goog.require calls would then matter. We want to enforce that most of
      // the time the order of the require calls does not matter.
      controller.defer(function() {
        load();
      });
      return;
    }
    // TODO: Externs are missing onreadystatechange for
    // HTMLDocument.
    /** @type {?} */
    var doc = goog.global.document;

    if (isEs6 && goog.inHtmlDocument_() && goog.isDocumentLoading_()) {
      goog.Dependency.defer_ = true;
      // Transpiled ES6 modules still need to load like regular ES6 modules,
      // aka only after the document is interactive.
      controller.pause();
      var oldCallback = doc.onreadystatechange;
      doc.onreadystatechange = function() {
        if (doc.readyState == 'interactive') {
          doc.onreadystatechange = oldCallback;
          load();
          controller.resume();
        }
        if (typeof oldCallback === 'function') {
          oldCallback.apply(undefined, arguments);
        }
      };
    } else {
      // Always eval on old IE.
      if (!goog.inHtmlDocument_() || !goog.isDocumentLoading_()) {
        load();
      } else {
        fetchInOwnScriptThenLoad();
      }
    }
  };


  /**
   * @param {string} contents
   * @return {string}
   * @abstract
   */
  goog.TransformedDependency.prototype.transform = function(contents) {};


  /**
   * An ES6 module dependency that was transpiled to a jscomp module outside
   * of the debug loader, e.g. server side.
   *
   * @param {string} path Absolute path of this script.
   * @param {string} relativePath Path of this script relative to goog.basePath.
   * @param {!Array<string>} provides goog.provided or goog.module symbols
   *     in this file.
   * @param {!Array<string>} requires goog symbols or relative paths to Closure
   *     this depends on.
   * @param {!Object<string, string>} loadFlags
   * @struct @constructor
   * @extends {goog.TransformedDependency}
   */
  goog.PreTranspiledEs6ModuleDependency = function(
      path, relativePath, provides, requires, loadFlags) {
    goog.PreTranspiledEs6ModuleDependency.base(
        this, 'constructor', path, relativePath, provides, requires, loadFlags);
  };
  goog.inherits(
      goog.PreTranspiledEs6ModuleDependency, goog.TransformedDependency);


  /**
   * @override
   * @param {string} contents
   * @return {string}
   */
  goog.PreTranspiledEs6ModuleDependency.prototype.transform = function(
      contents) {
    return contents;
  };


  /**
   * A goog.module, transpiled or not. Will always perform some minimal
   * transformation even when not transpiled to wrap in a goog.loadModule
   * statement.
   *
   * @param {string} path Absolute path of this script.
   * @param {string} relativePath Path of this script relative to goog.basePath.
   * @param {!Array<string>} provides goog.provided or goog.module symbols
   *     in this file.
   * @param {!Array<string>} requires goog symbols or relative paths to Closure
   *     this depends on.
   * @param {!Object<string, string>} loadFlags
   * @struct @constructor
   * @extends {goog.TransformedDependency}
   */
  goog.GoogModuleDependency = function(
      path, relativePath, provides, requires, loadFlags) {
    goog.GoogModuleDependency.base(
        this, 'constructor', path, relativePath, provides, requires, loadFlags);
  };
  goog.inherits(goog.GoogModuleDependency, goog.TransformedDependency);


  /**
   * @override
   * @param {string} contents
   * @return {string}
   */
  goog.GoogModuleDependency.prototype.transform = function(contents) {
    if (!goog.LOAD_MODULE_USING_EVAL || goog.global.JSON === undefined) {
      return '' +
          'goog.loadModule(function(exports) {' +
          '"use strict";' + contents +
          '\n' +  // terminate any trailing single line comment.
          ';return exports' +
          '});' +
          '\n//# sourceURL=' + this.path + '\n';
    } else {
      return '' +
          'goog.loadModule(' +
          goog.global.JSON.stringify(
              contents + '\n//# sourceURL=' + this.path + '\n') +
          ');';
    }
  };


  /**
   * @param {string} relPath
   * @param {!Array<string>|undefined} provides
   * @param {!Array<string>} requires
   * @param {boolean|!Object<string>=} opt_loadFlags
   * @see goog.addDependency
   */
  goog.DebugLoader_.prototype.addDependency = function(
      relPath, provides, requires, opt_loadFlags) {
    provides = provides || [];
    relPath = relPath.replace(/\\/g, '/');
    var path = goog.normalizePath_(goog.basePath + relPath);
    if (!opt_loadFlags || typeof opt_loadFlags === 'boolean') {
      opt_loadFlags = opt_loadFlags ? {'module': goog.ModuleType.GOOG} : {};
    }
    var dep = this.factory_.createDependency(
        path, relPath, provides, requires, opt_loadFlags);
    this.dependencies_[path] = dep;
    for (var i = 0; i < provides.length; i++) {
      this.idToPath_[provides[i]] = path;
    }
    this.idToPath_[relPath] = path;
  };


  /**
   * Creates goog.Dependency instances for the debug loader to load.
   *
   * Should be overridden to have the debug loader use custom subclasses of
   * goog.Dependency.
   *
   * @struct @constructor
   */
  goog.DependencyFactory = function() {};


  /**
   * @param {string} path Absolute path of the file.
   * @param {string} relativePath Path relative to closure’s base.js.
   * @param {!Array<string>} provides Array of provided goog.provide/module ids.
   * @param {!Array<string>} requires Array of required goog.provide/module /
   *     relative ES6 module paths.
   * @param {!Object<string, string>} loadFlags
   * @return {!goog.Dependency}
   */
  goog.DependencyFactory.prototype.createDependency = function(
      path, relativePath, provides, requires, loadFlags) {
    // MOE:begin_strip
    var provide, require;
    for (var i = 0; provide = provides[i]; i++) {
      goog.dependencies_.nameToPath[provide] = relativePath;
      goog.dependencies_.loadFlags[relativePath] = loadFlags;
    }
    for (var j = 0; require = requires[j]; j++) {
      if (!(relativePath in goog.dependencies_.requires)) {
        goog.dependencies_.requires[relativePath] = {};
      }
      goog.dependencies_.requires[relativePath][require] = true;
    }
    // MOE:end_strip

    if (loadFlags['module'] == goog.ModuleType.GOOG) {
      return new goog.GoogModuleDependency(
          path, relativePath, provides, requires, loadFlags);
    } else {
      if (loadFlags['module'] == goog.ModuleType.ES6) {
        if (goog.ASSUME_ES_MODULES_TRANSPILED) {
          return new goog.PreTranspiledEs6ModuleDependency(
              path, relativePath, provides, requires, loadFlags);
        } else {
          return new goog.Es6ModuleDependency(
              path, relativePath, provides, requires, loadFlags);
        }
      } else {
        return new goog.Dependency(
            path, relativePath, provides, requires, loadFlags);
      }
    }
  };


  /** @private @const */
  goog.debugLoader_ = new goog.DebugLoader_();


  /**
   * Loads the Closure deps.js file.
   *
   * Exposed a public function so after base is loaded, and
   * then this can be called to load the closure deps.js file.
   */
  goog.loadClosureDeps = function() {
    goog.debugLoader_.loadClosureDeps();
  };


  /**
   * Sets the dependency factory, which can be used to create custom
   * goog.Dependency implementations to control how dependencies are loaded.
   *
   * Note:
   * You can call goog.loadClosureDeps to load the Closure dependency file
   * later, after your factory is injected.
   *
   * @param {!goog.DependencyFactory} factory
   */
  goog.setDependencyFactory = function(factory) {
    goog.debugLoader_.setDependencyFactory(factory);
  };


  /**
   * Trusted Types policy for the debug loader.
   * @private @const {?TrustedTypePolicy}
   */
  goog.TRUSTED_TYPES_POLICY_ = goog.TRUSTED_TYPES_POLICY_NAME ?
      goog.createTrustedTypesPolicy(goog.TRUSTED_TYPES_POLICY_NAME + '#base') :
      null;
}


if (!COMPILED) {
  /**
   * Trusted Types for running dev servers.
   *
   * @private @const
   */
  goog.CLOSURE_EVAL_PREFILTER_ = goog.global.trustedTypes &&
          goog.createTrustedTypesPolicy('goog#base#devonly#eval') ||
      {createScript: goog.identity_};
}

/**
 * go/goog-code-location-design
 * @enum {string}
 */
goog.CodeLocation = {
  // Enums cannot be empty,
  DO_NOT_USE: '',
  // and need multiple distinct values so TS doesn't think `goog.CodeLocation`
  // returns a unique singleton value.
  DO_NOT_USE_ME_EITHER: '.',
};

/**
 * Returns the stack location of this function's caller's caller.
 * e.g:
 *   1| function foo() {
 *   2|    console.log(goog.callerLocation());
 *   3| }
 *   4| function bar() {
 *   5|    foo(); // this is the code location that goog.callerLocation returns
 *   6| }
 *   7| bar();
 *
 *  -> prints "at bar (...filepath.ts:5:4)" (i.e. foo() call on line 5)
 *
 * @return {!goog.CodeLocation}
 */
goog.callerLocation = function() {
  if (!COMPILED) {
    var err = new Error();
    var stack = err.stack;
    /**
     * We’re using index 3 for the stack split because:
     * - index [1] returns `const err = new Error();` in base.js (above line)
     * - index [2] returns function annotated with a goog.CodeLocation default
     * parameter, which does the call to goog.callerLocation
     * - index [3] returns
     * the users call to the function which calls goog.callerLocation
     */
    if (stack) stack = stack.split(/\n/g)[3];
    if (stack) stack = stack.trim();
    return /** @type {!goog.CodeLocation} */ (stack || '');
  }
  return /** @type {!goog.CodeLocation} */ ('');
};


/**
 * Returns a stable relatively short obfuscated string for a given input
 * string literal.
 *
 * It is guaranteed that:
 * 1. goog.callerLocationIdInternalDoNotCallOrElse("foo") !=
 * goog.callerLocationIdInternalDoNotCallOrElse("bar")
 * 2. goog.callerLocationIdInternalDoNotCallOrElse("foo") ==
 * goog.callerLocationIdInternalDoNotCallOrElse("foo")
 *
 * In unobfuscated mode, the string is just returned with '_' appended to mark
 * the processing. Unobfuscated mode is the "u"  and "du" modes in MSS, or
 * running a web dev server.
 * @param {string} id The identifier to obfuscate.
 * @return {!goog.CodeLocation}
 *
 * @idGenerator {consistent}
 */
goog.callerLocationIdInternalDoNotCallOrElse = function(id) {
  return /** @type {!goog.CodeLocation} */ (id);
};
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview
 * Hand-modified Closure version of tslib.js.
 * These use the literal space optimized code from TypeScript for
 * compatibility.
 *
 * @suppress {undefinedVars}
 */

// Do not use @license

/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */

goog.module('google3.third_party.javascript.tslib.tslib');

/** @suppress {missingPolyfill} the code below intentionally feature-tests. */
var extendStatics = Object.setPrototypeOf ||
    // LOCAL MODIFICATION: b/241217304. Remove usages of __proto__.
    function(d, b) {
      for (var p in b)
        if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
    };

/**
 * @param {?} d
 * @param {?} b
 */
exports.__extends = function(d, b) {
  // LOCAL MODIFICATION: In Cobalt 11 `typeof Event` is 'object' not 'function'.
  // In addition, YouTube Mobile JavaScript bans usage of `Event` via a
  // conformance test so we check it via goog.global. We first verify that the
  // parent class, b, is not undefined (i.e. when `Event` is not present).
  if (typeof b !== 'function' && b !== null && (b === undefined || b !== goog.global['Event']))
    throw new TypeError(
        'Class extends value ' + String(b) + ' is not a constructor or null');
  extendStatics(d, b);
  /** @constructor */
  function __() {
    /** @type {?} */ (this).constructor = d;
  }
  d.prototype =
      b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
};

/** @type {typeof Object.assign} */
exports.__assign = Object.assign || /** @return {?} */ function(/** ? */ t) {
  for (var s, i = 1, n = arguments.length; i < n; i++) {
    s = arguments[i];
    for (var p in s)
      if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
  }
  return t;
};

/**
 * @param {?} s
 * @param {?} e
 * @return {?}
 */
exports.__rest = function(s, e) {
  var t = {};
  for (var p in s)
    if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
      t[p] = s[p];
  if (s != null && typeof Object.getOwnPropertySymbols === 'function')
    for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
      if (e.indexOf(p[i]) < 0 &&
          Object.prototype.propertyIsEnumerable.call(s, p[i]))
        t[p[i]] = s[p[i]];
    }
  return t;
};

/**
 * @param {?} decorators
 * @param {T} target
 * @param {?=} key
 * @param {?=} desc
 * @return {T}
 * @template T
 */
exports.__decorate = function(decorators, target, key, desc) {
  var c = arguments.length,
      r = c < 3     ? target :
      desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) :
                      desc,
      d;
  // LOCAL MODIFICATION: use quoted property access to work around b/77140019.
  if (Reflect && typeof Reflect === 'object' &&
      typeof Reflect['decorate'] === 'function')
    r = Reflect['decorate'](decorators, target, key, desc);
  else
    for (var i = decorators.length - 1; i >= 0; i--)
      if (d = decorators[i])
        r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
  return c > 3 && r && Object.defineProperty(target, key, r), r;
};

/**
 * @param {?} paramIndex
 * @param {?} decorator
 * @return {?}
 */
exports.__param = function(paramIndex, decorator) {
  return function(target, key) {
    decorator(target, key, paramIndex);
  };
};

// LOCAL MODIFICATION: Exclude the following functions:
// __esDecorate
// __runInitializers
// __propKey

exports.__setFunctionName = function(f, name, prefix) {
  if (typeof name === 'symbol')
    name = name.description ? '['.concat(name.description, ']') : '';
  return Object.defineProperty(f, 'name', {
    configurable: true,
    value: prefix ? ''.concat(prefix, ' ', name) : name
  });
};

/**
 * @param {?} metadataKey
 * @param {?} metadataValue
 * @return {?}
 */
exports.__metadata = function(metadataKey, metadataValue) {
  // LOCAL MODIFICATION: use quoted property access to work around b/77140019.
  if (Reflect && typeof Reflect === 'object' &&
      typeof Reflect['metadata'] === 'function')
    return Reflect['metadata'](metadataKey, metadataValue);
};

/**
 * @template T
 * @param {T} thisArg
 * @param {?} _arguments
 * @param {?} P
 * @param {function(this:T)} generator
 * @return {?}
 */
exports.__awaiter = function(thisArg, _arguments, P, generator) {
  function adopt(value) {
    return value instanceof P ? value : new P(function(resolve) {
      resolve(value);
    });
  }
  return new (P || (P = Promise))(function(resolve, reject) {
    function fulfilled(value) {
      try {
        // LOCAL MODIFICATION: Cannot express the function + keys pattern in the
        // Closure Compiler, so we escape generator.next with the `?` type.
        step(/** @type {?} */ (generator).next(value));
      } catch (e) {
        reject(e);
      }
    }
    function rejected(value) {
      try {
        step(generator['throw'](value));
      } catch (e) {
        reject(e);
      }
    }
    function step(result) {
      result.done ? resolve(result.value) :
                    adopt(result.value).then(fulfilled, rejected);
    }
    step((generator = generator.apply(thisArg, _arguments || [])).next());
  });
};

/**
 * @param {?} thisArg
 * @param {?} body
 * @return {?}
 */
exports.__generator = function(thisArg, body) {
  var _ = {
    label: 0,
    sent: function() {
      if (t[0] & 1) throw /** @type {!Error} */ (t[1]);
      return t[1];
    },
    trys: [],
    ops: []
  },
      f, y, t,
      g = Object.create(
          (typeof Iterator === 'function' ? Iterator : Object).prototype);
  // LOCAL MODIFICATION: access property quoted to compile and prevent renaming.
  return g['next'] = verb(0), g['throw'] = verb(1), g['return'] = verb(2),
         typeof Symbol === 'function' && (g[Symbol.iterator] = function() {
           return /** @type {?} */ (this);
         }), g;
  function verb(n) {
    return function(v) {
      return step([n, v]);
    };
  }
  /**
   * @suppress {strictMissingProperties} TODO: Remove
   * strictMissingProperties suppression after b/214427036 is fixed
   */
  function step(op) {
    if (f) throw new TypeError('Generator is already executing.');
    while (g && (g = 0, op[0] && (_ = 0)), _) try {
        if (f = 1,
            y &&
                (t = op[0] & 2 ? y['return'] :
                     op[0] ? y['throw'] || ((t = y['return']) && t.call(y), 0) :
                             y.next) &&
                !(t = t.call(y, op[1])).done)
          return t;
        if (y = 0, t) op = [op[0] & 2, t.value];
        switch (op[0]) {
          case 0:
          case 1:
            t = op;
            break;
          case 4:
            _.label++;
            return {value: op[1], done: false};
          case 5:
            _.label++;
            y = op[1];
            op = [0];
            continue;
          case 7:
            op = _.ops.pop();
            _.trys.pop();
            continue;
          default:
            if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) &&
                (op[0] === 6 || op[0] === 2)) {
              _ = 0;
              continue;
            }
            if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) {
              _.label = op[1];
              break;
            }
            if (op[0] === 6 && _.label < t[1]) {
              _.label = t[1];
              t = op;
              break;
            }
            if (t && _.label < t[2]) {
              _.label = t[2];
              _.ops.push(op);
              break;
            }
            if (t[2]) _.ops.pop();
            _.trys.pop();
            continue;
        }
        op = body.call(thisArg, _);
      } catch (e) {
        op = [6, e];
        y = 0;
      } finally {
        f = t = 0;
      }
    if (op[0] & 5) throw /** @type {!Error} */ (op[1]);
    return {value: op[0] ? op[1] : void 0, done: true};
  }
};

/**
 * @param {?} m
 * @param {?} o
 */
exports.__exportStar = function(m, o) {
  for (var p in m)
    if (p !== 'default' && !Object.prototype.hasOwnProperty.call(o, p))
      // LOCAL MODIFICATION: Using __createBinding makes o[p] non-settable which
      // breaks code like the following (valid for ESM modules):
      // # file1.ts
      //   export const foo = 'foo';
      //   export const bar = 'bar';
      // # file2.ts
      //   export * as m from './file1';
      //   export const foo = 'a new foo value';
      o[p] = m[p];
};

// LOCAL MODIFICATION: Exclude the following function:
// __createBinding

/**
 * @param {?} o
 * @return {?}
 */
exports.__values = function(o) {
  var s = typeof Symbol === 'function' && Symbol.iterator, m = s && o[/** @type {symbol} */ (s)], i = 0;
  if (m) return m.call(o);
  if (o && typeof o.length === 'number')
    return {
      next: function() {
        if (o && i >= o.length) o = void 0;
        return {value: o && o[i++], done: !o};
      }
    };
  throw new TypeError(
      s ? 'Object is not iterable.' : 'Symbol.iterator is not defined.');
};

/**
 * @param {?} o
 * @param {?=} n
 * @return {?}
 */
exports.__read = function(o, n) {
  var m = typeof Symbol === 'function' && o[Symbol.iterator];
  if (!m) return o;
  var i = m.call(o), r, ar = [], e;
  try {
    while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
  } catch (error) {
    e = {error: error};
  } finally {
    try {
      if (r && !r.done && (m = i['return'])) m.call(i);
    } finally {
      if (e) throw /** @type {!Error} */ (e.error);
    }
  }
  return ar;
};

/** @deprecated */
exports.__spread = function() {
  for (var ar = [], i = 0; i < arguments.length; i++)
    ar = ar.concat(exports.__read(arguments[i]));
  return ar;
};

/** @deprecated */
exports.__spreadArrays = function() {
  for (var s = 0, i = 0, il = arguments.length; i < il; i++)
    s += arguments[i].length;
  for (var r = Array(s), k = 0, i = 0; i < il; i++)
    for (var a = arguments[i], j = 0, jl = a.length; j < jl; j++, k++)
      r[k] = a[j];
  return r;
};

/**
 * @param {!Array<?>} to
 * @param {!Array<?>} from
 * @param {!Array<?>} pack
 * @return {!Array<?>}
 */
exports.__spreadArray = function(to, from, pack) {
  if (pack || arguments.length === 2)
    for (var i = 0, l = from.length, ar; i < l; i++) {
      if (ar || !(i in from)) {
        if (!ar) ar = Array.prototype.slice.call(from, 0, i);
        ar[i] = from[i];
      }
    }
  return to.concat(ar || Array.prototype.slice.call(from));
};

/**
 * @constructor
 * @this {?}
 * @param {?} v
 * @return {?}
 */
exports.__await = function(v) {
  return this instanceof exports.__await ? (this.v = v, this) :
                                           new exports.__await(v);
};

/**
 * @template T
 * @param {T} thisArg
 * @param {?} _arguments
 * @param {function(this:T)} generator
 * @return {?}
 */
exports.__asyncGenerator = function(thisArg, _arguments, generator) {
  if (!Symbol.asyncIterator)
    throw new TypeError('Symbol.asyncIterator is not defined.');
  var g = generator.apply(thisArg, _arguments || []), i, q = [];
  return i = Object.create(
             (typeof AsyncIterator === 'function' ? AsyncIterator : Object)
                 .prototype),
         verb('next'), verb('throw'), verb('return', awaitReturn),
         i[Symbol.asyncIterator] = function() {
           return /** @type {?} */ (this);
         }, i;
  function awaitReturn(f) {
    return function(v) {
      return Promise.resolve(v).then(f, reject);
    };
  }
  /**
   * @param {?} n
   * @param {?=} f
   * @return {?}
   */
  function verb(n, f) {
    if (g[n]) {
      i[n] = function(v) {
        return new Promise(function(a, b) {
          q.push([n, v, a, b]) > 1 || resume(n, v);
        });
      };
      if (f) i[n] = f(i[n]);
    }
  }
  function resume(n, v) {
    try {
      step(g[n](v));
    } catch (e) {
      settle(q[0][3], e);
    }
  }
  function step(r) {
    r.value instanceof exports.__await ?
        Promise.resolve(/** @type {?} */ (r.value).v).then(fulfill, reject) :
        settle(q[0][2], r);
  }
  function fulfill(value) {
    resume('next', value);
  }
  function reject(value) {
    resume('throw', value);
  }
  function settle(f, v) {
    if (f(v), q.shift(), q.length) resume(q[0][0], q[0][1]);
  }
};

/**
 * @param {?} o
 * @return {?}
 */
exports.__asyncDelegator = function(o) {
  var i, p;
  return i = {}, verb('next'), verb('throw', function(e) {
           throw e;
         }), verb('return'), i[Symbol.iterator] = function() {
    return /** @type {?} */ (this);
  }, i;
  /**
   * @param {?} n
   * @param {?=} f
   * @return {?}
   */
  function verb(n, f) {
    i[n] = o[n] ? function(v) {
      // LOCAL MODIFICATION: If __await is called without new, it calls itself
      // again with new. We mark __await as a constructor above so need to
      // directly call new to appease the compiler. Same behavior though.
      return (p = !p) ? {value: new exports.__await(o[n](v)), done: false} : f ? f(v) : v;
    } : f;
  }
};

/**
 * @param {?} o
 * @return {?}
 */
exports.__asyncValues = function(o) {
  if (!Symbol.asyncIterator)
    throw new TypeError('Symbol.asyncIterator is not defined.');
  var m = o[Symbol.asyncIterator], i;
  return m ?
      m.call(o) :
      (o = typeof __values === 'function' ? __values(o) : o[Symbol.iterator](),
       i = {}, verb('next'), verb('throw'), verb('return'),
       i[Symbol.asyncIterator] = function() {
         return /** @type {?} */ (this);
       }, i);
  function verb(n) {
    i[n] = o[n] && function(v) {
      return new Promise(function(resolve, reject) {
        v = o[n](v), settle(resolve, reject, v.done, v.value);
      });
    };
  }
  function settle(resolve, reject, d, v) {
    Promise.resolve(v).then(function(v) {
      resolve({value: v, done: d});
    }, reject);
  }
};

/**
 * @param {?=} cooked
 * @param {?=} raw
 * @return {?}
 */
exports.__makeTemplateObject = function(cooked, raw) {
  if (Object.defineProperty) {
    Object.defineProperty(cooked, 'raw', {value: raw});
  } else {
    cooked.raw = raw;
  }
  return cooked;
};

// LOCAL MODIFICATION: Exclude the following functions:
// __importStar
// __importDefault

/**
 * @param {?} receiver
 * @param {?} state
 * @param {?} kind
 * @param {?} f
 * @return {?}
 */
exports.__classPrivateFieldGet = function(receiver, state, kind, f) {
  if (kind === 'a' && !f)
    throw new TypeError('Private accessor was defined without a getter');
  if (typeof state === 'function' ? receiver !== state || !f :
                                    !state.has(receiver))
    throw new TypeError(
        'Cannot read private member from an object whose class did not declare it');
  return kind === 'm' ? f :
      kind === 'a'    ? f.call(receiver) :
      f               ? f.value :
                        state.get(receiver);
};

/**
 * @param {?} receiver
 * @param {?} state
 * @param {?} value
 * @param {?} kind
 * @param {?} f
 * @return {?}
 */
exports.__classPrivateFieldSet = function(receiver, state, value, kind, f) {
  if (kind === 'm') throw new TypeError('Private method is not writable');
  if (kind === 'a' && !f)
    throw new TypeError('Private accessor was defined without a setter');
  if (typeof state === 'function' ? receiver !== state || !f :
                                    !state.has(receiver))
    throw new TypeError(
        'Cannot write private member to an object whose class did not declare it');
  return (kind === 'a' ? f.call(receiver, value) :
              f        ? f.value = value :
                         state.set(receiver, value)),
         value;
};

/**
 * @param {?} state
 * @param {?} receiver
 * @return {?}
 */
exports.__classPrivateFieldIn = function(state, receiver) {
  if (receiver === null ||
      (typeof receiver !== 'object' && typeof receiver !== 'function'))
    throw new TypeError('Cannot use \'in\' operator on non-object');
  return typeof state === 'function' ? receiver === state : state.has(receiver);
};

/**
 * @param {?} env
 * @param {?} value
 * @param {?} async
 * @return {?}
 */
exports.__addDisposableResource = function(env, value, async) {
  if (value !== null && value !== void 0) {
    if (typeof value !== 'object' && typeof value !== 'function')
      throw new TypeError('Object expected.');
    var dispose, inner;
    // LOCAL MODIFICATION: Cast to `valueObject` to explain to the Closure
    // Compiler that `value` can't be `null` nor `undefined` here.
    var valueObject = /** @type {!Object} */ (value);
    if (async) {
      if (!Symbol.asyncDispose)
        throw new TypeError('Symbol.asyncDispose is not defined.');
      dispose = valueObject[Symbol.asyncDispose];
    }
    if (dispose === void 0) {
      if (!Symbol.dispose)
        throw new TypeError('Symbol.dispose is not defined.');
      dispose = valueObject[Symbol.dispose];
      if (async) inner = dispose;
    }
    if (typeof dispose !== 'function')
      throw new TypeError('Object not disposable.');
    if (inner)
      dispose = function() {
        try {
          inner.call(/** @type {?} */ (this));
        } catch (e) {
          return Promise.reject(e);
        }
      };
    env.stack.push({value: value, dispose: dispose, async: async});
  } else if (async) {
    env.stack.push({async: true});
  }
  return value;
};

// LOCAL MODIFICATION: Not polyfilling SuppressedError here. It's polyfilled at
// google3/third_party/java_src/jscomp/java/com/google/javascript/jscomp/js/es6/dispose.js

/**
 * @param {?} env
 * @return {?}
 */
exports.__disposeResources = function(env) {
  function fail(e) {
    env.error = env.hasError ?
        // LOCAL MODIFICATION: Use SuppressedError instead of _SuppressedError.
        new SuppressedError(
            e, env.error, 'An error was suppressed during disposal.') :
        e;
    env.hasError = true;
  }
  var r, s = 0;
  function next() {
    while (r = env.stack.pop()) {
      try {
        if (!r.async && s === 1)
          return s = 0, env.stack.push(r), Promise.resolve().then(next);
        if (r.dispose) {
          var result = r.dispose.call(r.value);
          if (r.async)
            return s |= 2, Promise.resolve(result).then(next, function(e) {
              fail(e);
              return next();
            });
        } else
          s |= 1;
      } catch (e) {
        fail(e);
      }
    }
    if (s === 1)
      return env.hasError ? Promise.reject(env.error) : Promise.resolve();
    if (env.hasError) throw env.error;
  }
  return next();
};

// LOCAL MODIFICATION: Not including __rewriteRelativeImportExtension

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/util.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/util.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
var util;
(function (util) {
    /** @typedef {?} */
    var AssertEqual;
    /** @typedef {?} */
    exports.isAny;
    /** @type {?} */
    util.assertEqual = (/**
     * @template A, B
     * @param {?} _
     * @return {void}
     */
    (_) => { });
    /**
     * @template T
     * @param {?} _arg
     * @return {void}
     */
    function assertIs(_arg) { }
    util.assertIs = assertIs;
    /**
     * @param {?} _x
     * @return {?}
     */
    function assertNever(_x) {
        throw new Error();
    }
    util.assertNever = assertNever;
    /** @typedef {?} */
    exports.Omit;
    /** @typedef {?} */
    exports.OmitKeys;
    /** @typedef {?} */
    exports.MakePartial;
    /** @typedef {?} */
    exports.Exactly;
    /** @typedef {?} */
    exports.InexactPartial;
    /** @type {?} */
    util.arrayToEnum = (/**
     * @template T, U
     * @param {?} items
     * @return {?}
     */
    (items) => {
        /** @type {?} */
        const obj = {};
        for (const item of items) {
            obj[item] = item;
        }
        return obj;
    });
    /** @type {?} */
    util.getValidEnumValues = (/**
     * @param {?} obj
     * @return {!Array<?>}
     */
    (obj) => {
        /** @type {!Array<string>} */
        const validKeys = util.objectKeys(obj).filter((/**
         * @param {?} k
         * @return {boolean}
         */
        (k) => typeof obj[obj[k]] !== "number"));
        /** @type {?} */
        const filtered = {};
        for (const k of validKeys) {
            filtered[k] = obj[k];
        }
        return util.objectValues(filtered);
    });
    /** @type {?} */
    util.objectValues = (/**
     * @param {?} obj
     * @return {!Array<?>}
     */
    (obj) => {
        return util.objectKeys(obj).map((/**
         * @param {string} e
         * @return {?}
         */
        function (e) {
            return obj[e];
        }));
    });
    /** @type {?} */
    util.objectKeys = typeof Object.keys === "function" // eslint-disable-line ban/ban
        ? (/**
         * @param {?} obj
         * @return {!Array<string>}
         */
        (obj) => Object.keys(obj) // eslint-disable-line ban/ban
        )
        : (/**
         * @param {?} object
         * @return {!Array<string>}
         */
        (object) => {
            /** @type {!Array<?>} */
            const keys = [];
            for (const key in object) {
                if (Object.prototype.hasOwnProperty.call(object, key)) {
                    keys.push(key);
                }
            }
            return keys;
        });
    /** @type {?} */
    util.find = (/**
     * @template T
     * @param {!Array<?>} arr
     * @param {?} checker
     * @return {(undefined|?)}
     */
    (arr, checker) => {
        for (const item of arr) {
            if (checker(item))
                return item;
        }
        return undefined;
    });
    /** @typedef {?} */
    exports.identity;
    /** @typedef {?} */
    exports.flatten;
    /** @typedef {?} */
    exports.noUndefined;
    /** @type {function(*): boolean} */
    util.isInteger = typeof Number.isInteger === "function"
        ? (/**
         * @param {*} val
         * @return {boolean}
         */
        (val) => Number.isInteger(val) // eslint-disable-line ban/ban
        )
        : (/**
         * @param {*} val
         * @return {boolean}
         */
        (val) => typeof val === "number" && Number.isFinite(val) && Math.floor(val) === val);
    /**
     * @template T
     * @param {?} array
     * @param {string=} separator
     * @return {string}
     */
    function joinValues(array, separator = " | ") {
        return array.map((/**
         * @param {?} val
         * @return {?}
         */
        (val) => (typeof val === "string" ? `'${val}'` : val))).join(separator);
    }
    util.joinValues = joinValues;
    /** @type {?} */
    util.jsonStringifyReplacer = (/**
     * @param {string} _
     * @param {?} value
     * @return {?}
     */
    (_, value) => {
        if (typeof value === "bigint") {
            return (/** @type {bigint} */ (value)).toString();
        }
        return value;
    });
})(util || (util = {}));
exports.util = util;
var objectUtil;
(function (objectUtil) {
    /** @typedef {?} */
    exports.MergeShapes;
    /** @typedef {?} */
    var optionalKeys;
    /** @typedef {?} */
    var requiredKeys;
    /** @typedef {?} */
    exports.addQuestionMarks;
    /** @typedef {?} */
    exports.identity;
    /** @typedef {?} */
    exports.flatten;
    /** @typedef {?} */
    exports.noNeverKeys;
    /** @typedef {?} */
    exports.noNever;
    /** @type {?} */
    objectUtil.mergeShapes = (/**
     * @template U, T
     * @param {?} first
     * @param {?} second
     * @return {?}
     */
    (first, second) => {
        return {
            ...first,
            ...second, // second overwrites first
        };
    });
    /** @typedef {?} */
    exports.extendShape;
})(objectUtil || (objectUtil = {}));
exports.objectUtil = objectUtil;
/** @type {{string: string, nan: string, number: string, integer: string, float: string, boolean: string, date: string, bigint: string, symbol: string, function: string, undefined: string, null: string, array: string, object: string, unknown: string, promise: string, void: string, never: string, map: string, set: string}} */
exports.ZodParsedType = util.arrayToEnum([
    "string",
    "nan",
    "number",
    "integer",
    "float",
    "boolean",
    "date",
    "bigint",
    "symbol",
    "function",
    "undefined",
    "null",
    "array",
    "object",
    "unknown",
    "promise",
    "void",
    "never",
    "map",
    "set",
]);
/** @type {function(?): string} */
exports.getParsedType = (/**
 * @param {?} data
 * @return {string}
 */
(data) => {
    /** @type {string} */
    const t = typeof data;
    switch (t) {
        case "undefined":
            return exports.ZodParsedType.undefined;
        case "string":
            return exports.ZodParsedType.string;
        case "number":
            return Number.isNaN(data) ? exports.ZodParsedType.nan : exports.ZodParsedType.number;
        case "boolean":
            return exports.ZodParsedType.boolean;
        case "function":
            return exports.ZodParsedType.function;
        case "bigint":
            return exports.ZodParsedType.bigint;
        case "symbol":
            return exports.ZodParsedType.symbol;
        case "object":
            if (Array.isArray(data)) {
                return exports.ZodParsedType.array;
            }
            if (data === null) {
                return exports.ZodParsedType.null;
            }
            if (data.then && typeof data.then === "function" && data.catch && typeof data.catch === "function") {
                return exports.ZodParsedType.promise;
            }
            if (typeof Map !== "undefined" && data instanceof Map) {
                return exports.ZodParsedType.map;
            }
            if (typeof Set !== "undefined" && data instanceof Set) {
                return exports.ZodParsedType.set;
            }
            if (typeof Date !== "undefined" && data instanceof Date) {
                return exports.ZodParsedType.date;
            }
            return exports.ZodParsedType.object;
        default:
            return exports.ZodParsedType.unknown;
    }
});

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/ZodError.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/ZodError.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_typeAliases_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.typeAliases");
const tsickle_util_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util");
const tsickle___3 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.index");
const util_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util');
/** @typedef {?} */
var allKeys;
/** @typedef {{formErrors: !Array<?>, fieldErrors: ?}} */
exports.inferFlattenedErrors;
/** @typedef {{formErrors: !Array<?>, fieldErrors: ?}} */
exports.typeToFlattenedError;
/** @type {?} */
exports.ZodIssueCode = util_js_1.util.arrayToEnum([
    "invalid_type",
    "invalid_literal",
    "custom",
    "invalid_union",
    "invalid_union_discriminator",
    "invalid_enum_value",
    "unrecognized_keys",
    "invalid_arguments",
    "invalid_return_type",
    "invalid_date",
    "invalid_string",
    "too_small",
    "too_big",
    "invalid_intersection_types",
    "not_multiple_of",
    "not_finite",
]);
/** @typedef {{path: !Array<(string|number)>, message: (undefined|string)}} */
exports.ZodIssueBase;
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidTypeIssue() { }
exports.ZodInvalidTypeIssue = ZodInvalidTypeIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidTypeIssue.prototype.code;
    /**
     * @type {string}
     * @public
     */
    ZodInvalidTypeIssue.prototype.expected;
    /**
     * @type {string}
     * @public
     */
    ZodInvalidTypeIssue.prototype.received;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidLiteralIssue() { }
exports.ZodInvalidLiteralIssue = ZodInvalidLiteralIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidLiteralIssue.prototype.code;
    /**
     * @type {*}
     * @public
     */
    ZodInvalidLiteralIssue.prototype.expected;
    /**
     * @type {*}
     * @public
     */
    ZodInvalidLiteralIssue.prototype.received;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodUnrecognizedKeysIssue() { }
exports.ZodUnrecognizedKeysIssue = ZodUnrecognizedKeysIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodUnrecognizedKeysIssue.prototype.code;
    /**
     * @type {!Array<string>}
     * @public
     */
    ZodUnrecognizedKeysIssue.prototype.keys;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidUnionIssue() { }
exports.ZodInvalidUnionIssue = ZodInvalidUnionIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidUnionIssue.prototype.code;
    /**
     * @type {!Array<!tsickle___3.ZodError<?>>}
     * @public
     */
    ZodInvalidUnionIssue.prototype.unionErrors;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidUnionDiscriminatorIssue() { }
exports.ZodInvalidUnionDiscriminatorIssue = ZodInvalidUnionDiscriminatorIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidUnionDiscriminatorIssue.prototype.code;
    /**
     * @type {!Array<(undefined|null|string|number|bigint|symbol|boolean)>}
     * @public
     */
    ZodInvalidUnionDiscriminatorIssue.prototype.options;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidEnumValueIssue() { }
exports.ZodInvalidEnumValueIssue = ZodInvalidEnumValueIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(string|number)}
     * @public
     */
    ZodInvalidEnumValueIssue.prototype.received;
    /**
     * @type {string}
     * @public
     */
    ZodInvalidEnumValueIssue.prototype.code;
    /**
     * @type {!Array<(string|number)>}
     * @public
     */
    ZodInvalidEnumValueIssue.prototype.options;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidArgumentsIssue() { }
exports.ZodInvalidArgumentsIssue = ZodInvalidArgumentsIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidArgumentsIssue.prototype.code;
    /**
     * @type {!tsickle___3.ZodError<?>}
     * @public
     */
    ZodInvalidArgumentsIssue.prototype.argumentsError;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidReturnTypeIssue() { }
exports.ZodInvalidReturnTypeIssue = ZodInvalidReturnTypeIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidReturnTypeIssue.prototype.code;
    /**
     * @type {!tsickle___3.ZodError<?>}
     * @public
     */
    ZodInvalidReturnTypeIssue.prototype.returnTypeError;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidDateIssue() { }
exports.ZodInvalidDateIssue = ZodInvalidDateIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidDateIssue.prototype.code;
}
/** @typedef {(string|{includes: string, position: (undefined|number)}|{startsWith: string}|{endsWith: string})} */
exports.StringValidation;
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidStringIssue() { }
exports.ZodInvalidStringIssue = ZodInvalidStringIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidStringIssue.prototype.code;
    /**
     * @type {(string|{includes: string, position: (undefined|number)}|{startsWith: string}|{endsWith: string})}
     * @public
     */
    ZodInvalidStringIssue.prototype.validation;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodTooSmallIssue() { }
exports.ZodTooSmallIssue = ZodTooSmallIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodTooSmallIssue.prototype.code;
    /**
     * @type {(number|bigint)}
     * @public
     */
    ZodTooSmallIssue.prototype.minimum;
    /**
     * @type {boolean}
     * @public
     */
    ZodTooSmallIssue.prototype.inclusive;
    /**
     * @type {(undefined|boolean)}
     * @public
     */
    ZodTooSmallIssue.prototype.exact;
    /**
     * @type {string}
     * @public
     */
    ZodTooSmallIssue.prototype.type;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodTooBigIssue() { }
exports.ZodTooBigIssue = ZodTooBigIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodTooBigIssue.prototype.code;
    /**
     * @type {(number|bigint)}
     * @public
     */
    ZodTooBigIssue.prototype.maximum;
    /**
     * @type {boolean}
     * @public
     */
    ZodTooBigIssue.prototype.inclusive;
    /**
     * @type {(undefined|boolean)}
     * @public
     */
    ZodTooBigIssue.prototype.exact;
    /**
     * @type {string}
     * @public
     */
    ZodTooBigIssue.prototype.type;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodInvalidIntersectionTypesIssue() { }
exports.ZodInvalidIntersectionTypesIssue = ZodInvalidIntersectionTypesIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodInvalidIntersectionTypesIssue.prototype.code;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodNotMultipleOfIssue() { }
exports.ZodNotMultipleOfIssue = ZodNotMultipleOfIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodNotMultipleOfIssue.prototype.code;
    /**
     * @type {(number|bigint)}
     * @public
     */
    ZodNotMultipleOfIssue.prototype.multipleOf;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodNotFiniteIssue() { }
exports.ZodNotFiniteIssue = ZodNotFiniteIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodNotFiniteIssue.prototype.code;
}
/**
 * @record
 * tsickle: dropped extends: dropped extends of a type literal: ZodIssueBase
 */
function ZodCustomIssue() { }
exports.ZodCustomIssue = ZodCustomIssue;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ZodCustomIssue.prototype.code;
    /**
     * @type {(undefined|!Object<string,?>)}
     * @public
     */
    ZodCustomIssue.prototype.params;
}
/** @typedef {!Object<string,(!Array<string>|?)>} */
exports.DenormalizedError;
/** @typedef {(!tsickle___3.ZodCustomIssue|!tsickle___3.ZodInvalidArgumentsIssue|!tsickle___3.ZodInvalidDateIssue|!tsickle___3.ZodInvalidEnumValueIssue|!tsickle___3.ZodInvalidIntersectionTypesIssue|!tsickle___3.ZodInvalidLiteralIssue|!tsickle___3.ZodInvalidReturnTypeIssue|!tsickle___3.ZodInvalidStringIssue|!tsickle___3.ZodInvalidTypeIssue|!tsickle___3.ZodInvalidUnionDiscriminatorIssue|!tsickle___3.ZodInvalidUnionIssue|!tsickle___3.ZodNotFiniteIssue|!tsickle___3.ZodNotMultipleOfIssue|!tsickle___3.ZodTooBigIssue|!tsickle___3.ZodTooSmallIssue|!tsickle___3.ZodUnrecognizedKeysIssue)} */
exports.ZodIssueOptionalMessage;
/** @typedef {?} */
exports.ZodIssue;
/** @type {function(?): string} */
exports.quotelessJson = (/**
 * @param {?} obj
 * @return {string}
 */
(obj) => {
    /** @type {string} */
    const json = JSON.stringify(obj, null, 2);
    return json.replace(/"([^"]+)":/g, "$1:");
});
/** @typedef {?} */
var recursiveZodFormattedError;
/** @typedef {?} */
exports.ZodFormattedError;
/** @typedef {?} */
exports.inferFormattedError;
/**
 * @template T
 * @extends {Error}
 */
class ZodError extends Error {
    /**
     * @public
     * @return {!Array<?>}
     */
    get errors() {
        return this.issues;
    }
    /**
     * @public
     * @param {!Array<?>} issues
     */
    constructor(issues) {
        super();
        this.issues = [];
        this.addIssue = (/**
         * @param {?} sub
         * @return {void}
         */
        (sub) => {
            this.issues = [...this.issues, sub];
        });
        this.addIssues = (/**
         * @param {!Array<?>=} subs
         * @return {void}
         */
        (subs = []) => {
            this.issues = [...this.issues, ...subs];
        });
        /** @type {!tsickle___3.ZodError<?>} */
        const actualProto = new.target.prototype;
        if (Object.setPrototypeOf) {
            // eslint-disable-next-line ban/ban
            Object.setPrototypeOf(this, actualProto);
        }
        else {
            ((/** @type {?} */ (this))).__proto__ = actualProto;
        }
        this.name = "ZodError";
        this.issues = issues;
    }
    /**
     * @public
     * @param {?=} _mapper
     * @return {?}
     */
    format(_mapper) {
        /** @type {function(?): ?} */
        const mapper = _mapper ||
            (/**
             * @param {?} issue
             * @return {string}
             */
            function (issue) {
                return issue.message;
            });
        /** @type {?} */
        const fieldErrors = (/** @type {?} */ ({ _errors: [] }));
        /** @type {function(!tsickle___3.ZodError<?>): void} */
        const processError = (/**
         * @param {!tsickle___3.ZodError<?>} error
         * @return {void}
         */
        (error) => {
            for (const issue of error.issues) {
                if (issue.code === "invalid_union") {
                    issue.unionErrors.map(processError);
                }
                else if (issue.code === "invalid_return_type") {
                    processError(issue.returnTypeError);
                }
                else if (issue.code === "invalid_arguments") {
                    processError(issue.argumentsError);
                }
                else if (issue.path.length === 0) {
                    ((/** @type {?} */ (fieldErrors)))._errors.push(mapper(issue));
                }
                else {
                    /** @type {?} */
                    let curr = fieldErrors;
                    /** @type {number} */
                    let i = 0;
                    while (i < issue.path.length) {
                        /** @type {(string|number)} */
                        const el = (/** @type {(string|number)} */ (issue.path[i]));
                        /** @type {boolean} */
                        const terminal = i === issue.path.length - 1;
                        if (!terminal) {
                            curr[el] = curr[el] || { _errors: [] };
                            // if (typeof el === "string") {
                            //   curr[el] = curr[el] || { _errors: [] };
                            // } else if (typeof el === "number") {
                            //   const errorArray: any = [];
                            //   errorArray._errors = [];
                            //   curr[el] = curr[el] || errorArray;
                            // }
                        }
                        else {
                            curr[el] = curr[el] || { _errors: [] };
                            curr[el]._errors.push(mapper(issue));
                        }
                        curr = curr[el];
                        i++;
                    }
                }
            }
        });
        processError(this);
        return fieldErrors;
    }
    /**
     * @public
     * @param {*} value
     * @return {void}
     */
    static assert(value) {
        if (!(value instanceof ZodError)) {
            throw new Error(`Not a ZodError: ${value}`);
        }
    }
    /**
     * @public
     * @return {string}
     */
    toString() {
        return this.message;
    }
    /**
     * @public
     * @return {string}
     */
    get message() {
        return JSON.stringify(this.issues, util_js_1.util.jsonStringifyReplacer, 2);
    }
    /**
     * @public
     * @return {boolean}
     */
    get isEmpty() {
        return this.issues.length === 0;
    }
    /**
     * @public
     * @template U
     * @param {function(?): U=} mapper
     * @return {?}
     */
    flatten(mapper = (/**
     * @param {?} issue
     * @return {?}
     */
    (issue) => (/** @type {?} */ (issue.message)))) {
        /** @type {?} */
        const fieldErrors = {};
        /** @type {!Array<U>} */
        const formErrors = [];
        for (const sub of this.issues) {
            if (sub.path.length > 0) {
                /** @type {(string|number)} */
                const firstEl = (/** @type {(string|number)} */ (sub.path[0]));
                fieldErrors[firstEl] = fieldErrors[firstEl] || [];
                fieldErrors[firstEl].push(mapper(sub));
            }
            else {
                formErrors.push(mapper(sub));
            }
        }
        return { formErrors, fieldErrors };
    }
    /**
     * @public
     * @return {{formErrors: !Array<string>, fieldErrors: ?}}
     */
    get formErrors() {
        return this.flatten();
    }
}
exports.ZodError = ZodError;
ZodError.create = (/**
 * @param {!Array<?>} issues
 * @return {!tsickle___3.ZodError<?>}
 */
(issues) => {
    /** @type {!tsickle___3.ZodError<?>} */
    const error = new ZodError(issues);
    return error;
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(!Array<?>): !tsickle___3.ZodError<?>}
     * @public
     */
    ZodError.create;
    /**
     * @type {!Array<?>}
     * @public
     */
    ZodError.prototype.issues;
    /**
     * @type {function(?): void}
     * @public
     */
    ZodError.prototype.addIssue;
    /**
     * @type {function(!Array<?>=): void}
     * @public
     */
    ZodError.prototype.addIssues;
}
/** @typedef {?} */
var stripPath;
/** @typedef {?} */
exports.IssueData;
/** @typedef {{defaultError: string, data: ?}} */
exports.ErrorMapCtx;
/** @typedef {function((!tsickle___3.ZodCustomIssue|!tsickle___3.ZodInvalidArgumentsIssue|!tsickle___3.ZodInvalidDateIssue|!tsickle___3.ZodInvalidEnumValueIssue|!tsickle___3.ZodInvalidIntersectionTypesIssue|!tsickle___3.ZodInvalidLiteralIssue|!tsickle___3.ZodInvalidReturnTypeIssue|!tsickle___3.ZodInvalidStringIssue|!tsickle___3.ZodInvalidTypeIssue|!tsickle___3.ZodInvalidUnionDiscriminatorIssue|!tsickle___3.ZodInvalidUnionIssue|!tsickle___3.ZodNotFiniteIssue|!tsickle___3.ZodNotMultipleOfIssue|!tsickle___3.ZodTooBigIssue|!tsickle___3.ZodTooSmallIssue|!tsickle___3.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} */
exports.ZodErrorMap;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/locales/en.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.locales.en');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/locales/en.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_ZodError_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError");
const tsickle_util_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util");
const ZodError_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError');
const util_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util');
/** @type {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} */
const errorMap = (/**
 * @param {(!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue)} issue
 * @param {{defaultError: string, data: ?}} _ctx
 * @return {{message: string}}
 */
(issue, _ctx) => {
    /** @type {string} */
    let message;
    switch (issue.code) {
        case ZodError_js_1.ZodIssueCode.invalid_type:
            if ((/** @type {!tsickle_ZodError_1.ZodInvalidTypeIssue} */ (issue)).received === util_js_1.ZodParsedType.undefined) {
                message = "Required";
            }
            else {
                message = `Expected ${(/** @type {!tsickle_ZodError_1.ZodInvalidTypeIssue} */ (issue)).expected}, received ${(/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidTypeIssue} */ (issue)).received))}`;
            }
            break;
        case ZodError_js_1.ZodIssueCode.invalid_literal:
            message = `Invalid literal value, expected ${JSON.stringify((/** @type {!tsickle_ZodError_1.ZodInvalidLiteralIssue} */ (issue)).expected, util_js_1.util.jsonStringifyReplacer)}`;
            break;
        case ZodError_js_1.ZodIssueCode.unrecognized_keys:
            message = `Unrecognized key(s) in object: ${util_js_1.util.joinValues((/** @type {!tsickle_ZodError_1.ZodUnrecognizedKeysIssue} */ (issue)).keys, ", ")}`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_union:
            message = `Invalid input`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_union_discriminator:
            message = `Invalid discriminator value. Expected ${util_js_1.util.joinValues((/** @type {!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue} */ (issue)).options)}`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_enum_value:
            message = `Invalid enum value. Expected ${util_js_1.util.joinValues((/** @type {!tsickle_ZodError_1.ZodInvalidEnumValueIssue} */ (issue)).options)}, received '${(/** @type {!tsickle_ZodError_1.ZodInvalidEnumValueIssue} */ (issue)).received}'`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_arguments:
            message = `Invalid function arguments`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_return_type:
            message = `Invalid function return type`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_date:
            message = `Invalid date`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_string:
            if (typeof (/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation === "object") {
                if ("includes" in (/** @type {({includes: string, position: (undefined|number)}|{startsWith: string}|{endsWith: string})} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation))) {
                    message = `Invalid input: must include "${(/** @type {{includes: string, position: (undefined|number)}} */ (issue.validation)).includes}"`;
                    if (typeof (/** @type {{includes: string, position: (undefined|number)}} */ (issue.validation)).position === "number") {
                        message = `${message} at one or more positions greater than or equal to ${(/** @type {{includes: string, position: (undefined|number)}} */ (issue.validation)).position}`;
                    }
                }
                else if ("startsWith" in (/** @type {({startsWith: string}|{endsWith: string})} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation))) {
                    message = `Invalid input: must start with "${(/** @type {{startsWith: string}} */ (issue.validation)).startsWith}"`;
                }
                else if ("endsWith" in (/** @type {{endsWith: string}} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation))) {
                    message = `Invalid input: must end with "${(/** @type {{endsWith: string}} */ (issue.validation)).endsWith}"`;
                }
                else {
                    util_js_1.util.assertNever((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation);
                }
            }
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation)) !== "regex") {
                message = `Invalid ${(/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodInvalidStringIssue} */ (issue)).validation))}`;
            }
            else {
                message = "Invalid";
            }
            break;
        case ZodError_js_1.ZodIssueCode.too_small:
            if ((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).type === "array")
                message = `Array must contain ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).exact ? "exactly" : (/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).inclusive ? `at least` : `more than`} ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).minimum} element(s)`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).type)) === "string")
                message = `String must contain ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).exact ? "exactly" : (/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).inclusive ? `at least` : `over`} ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).minimum} character(s)`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).type)) === "number")
                message = `Number must be ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).exact ? `exactly equal to ` : (/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).inclusive ? `greater than or equal to ` : `greater than `}${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).minimum}`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).type)) === "bigint")
                message = `Number must be ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).exact ? `exactly equal to ` : (/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).inclusive ? `greater than or equal to ` : `greater than `}${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).minimum}`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).type)) === "date")
                message = `Date must be ${(/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).exact ? `exactly equal to ` : (/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).inclusive ? `greater than or equal to ` : `greater than `}${new Date(Number((/** @type {!tsickle_ZodError_1.ZodTooSmallIssue} */ (issue)).minimum))}`;
            else
                message = "Invalid input";
            break;
        case ZodError_js_1.ZodIssueCode.too_big:
            if ((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).type === "array")
                message = `Array must contain ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).exact ? `exactly` : (/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).inclusive ? `at most` : `less than`} ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).maximum} element(s)`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).type)) === "string")
                message = `String must contain ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).exact ? `exactly` : (/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).inclusive ? `at most` : `under`} ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).maximum} character(s)`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).type)) === "number")
                message = `Number must be ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).exact ? `exactly` : (/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).inclusive ? `less than or equal to` : `less than`} ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).maximum}`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).type)) === "bigint")
                message = `BigInt must be ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).exact ? `exactly` : (/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).inclusive ? `less than or equal to` : `less than`} ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).maximum}`;
            else if ((/** @type {string} */ ((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).type)) === "date")
                message = `Date must be ${(/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).exact ? `exactly` : (/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).inclusive ? `smaller than or equal to` : `smaller than`} ${new Date(Number((/** @type {!tsickle_ZodError_1.ZodTooBigIssue} */ (issue)).maximum))}`;
            else
                message = "Invalid input";
            break;
        case ZodError_js_1.ZodIssueCode.custom:
            message = `Invalid input`;
            break;
        case ZodError_js_1.ZodIssueCode.invalid_intersection_types:
            message = `Intersection results could not be merged`;
            break;
        case ZodError_js_1.ZodIssueCode.not_multiple_of:
            message = `Number must be a multiple of ${(/** @type {!tsickle_ZodError_1.ZodNotMultipleOfIssue} */ (issue)).multipleOf}`;
            break;
        case ZodError_js_1.ZodIssueCode.not_finite:
            message = "Number must be finite";
            break;
        default:
            message = _ctx.defaultError;
            util_js_1.util.assertNever(issue);
    }
    return { message };
});
exports.default = errorMap;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/errors.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/errors.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_ZodError_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError");
const tsickle_en_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.locales.en");
const en_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.locales.en');
exports.defaultErrorMap = en_js_1.default;
/** @type {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} */
let overrideErrorMap = en_js_1.default;
/**
 * @param {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} map
 * @return {void}
 */
function setErrorMap(map) {
    overrideErrorMap = map;
}
exports.setErrorMap = setErrorMap;
/**
 * @return {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}}
 */
function getErrorMap() {
    return overrideErrorMap;
}
exports.getErrorMap = getErrorMap;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/parseUtil.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.parseUtil');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/parseUtil.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_ZodError_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError");
const tsickle_errors_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors");
const tsickle_en_3 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.locales.en");
const tsickle_util_4 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util");
const errors_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors');
const en_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.locales.en');
/** @type {function({data: ?, path: !Array<(string|number)>, errorMaps: !Array<function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}>, issueData: ?}): ?} */
exports.makeIssue = (/**
 * @param {{data: ?, path: !Array<(string|number)>, errorMaps: !Array<function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}>, issueData: ?}} params
 * @return {?}
 */
(params) => {
    const { data, path, errorMaps, issueData } = params;
    /** @type {!Array<(string|number)>} */
    const fullPath = [...path, ...(issueData.path || [])];
    /** @type {({message: (undefined|string), code: string, params: (undefined|!Object<string,?>), fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, argumentsError: !tsickle_ZodError_1.ZodError<?>, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), received: (string|number), code: string, options: !Array<(string|number)>, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, expected: *, received: *, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, returnTypeError: !tsickle_ZodError_1.ZodError<?>, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, validation: (string|{includes: string, position: (undefined|number)}|{startsWith: string}|{endsWith: string}), fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, expected: string, received: string, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, options: !Array<(undefined|null|string|number|bigint|symbol|boolean)>, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, unionErrors: !Array<!tsickle_ZodError_1.ZodError<?>>, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, multipleOf: (number|bigint), fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, maximum: (number|bigint), inclusive: boolean, exact: (undefined|boolean), type: string, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, minimum: (number|bigint), inclusive: boolean, exact: (undefined|boolean), type: string, fatal: (undefined|boolean), path: !Array<(string|number)>}|{message: (undefined|string), code: string, keys: !Array<string>, fatal: (undefined|boolean), path: !Array<(string|number)>})} */
    const fullIssue = {
        ...issueData,
        path: fullPath,
    };
    if (issueData.message !== undefined) {
        return {
            ...issueData,
            path: fullPath,
            message: issueData.message,
        };
    }
    /** @type {string} */
    let errorMessage = "";
    /** @type {!Array<function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}>} */
    const maps = errorMaps
        .filter((/**
     * @param {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} m
     * @return {boolean}
     */
    (m) => !!m))
        .slice()
        .reverse();
    for (const map of maps) {
        errorMessage = map(fullIssue, { data, defaultError: errorMessage }).message;
    }
    return {
        ...issueData,
        path: fullPath,
        message: errorMessage,
    };
});
/** @typedef {{path: !Array<(string|number)>, errorMap: function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}, async: boolean}} */
exports.ParseParams;
/** @typedef {(string|number)} */
exports.ParsePathComponent;
/** @typedef {!Array<(string|number)>} */
exports.ParsePath;
/** @type {!Array<(string|number)>} */
exports.EMPTY_PATH = [];
/**
 * @record
 */
function ParseContext() { }
exports.ParseContext = ParseContext;
/* istanbul ignore if */
if (false) {
    /**
     * @const {{issues: !Array<?>, contextualErrorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), async: boolean}}
     * @public
     */
    ParseContext.prototype.common;
    /**
     * @const {!Array<(string|number)>}
     * @public
     */
    ParseContext.prototype.path;
    /**
     * @const {(undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})}
     * @public
     */
    ParseContext.prototype.schemaErrorMap;
    /**
     * @const {(null|!ParseContext)}
     * @public
     */
    ParseContext.prototype.parent;
    /**
     * @const {?}
     * @public
     */
    ParseContext.prototype.data;
    /**
     * @const {string}
     * @public
     */
    ParseContext.prototype.parsedType;
}
/** @typedef {{data: ?, path: !Array<(string|number)>, parent: !ParseContext}} */
exports.ParseInput;
/**
 * @param {!ParseContext} ctx
 * @param {?} issueData
 * @return {void}
 */
function addIssueToContext(ctx, issueData) {
    /** @type {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} */
    const overrideMap = (0, errors_js_1.getErrorMap)();
    /** @type {?} */
    const issue = (0, exports.makeIssue)({
        issueData: issueData,
        data: ctx.data,
        path: ctx.path,
        errorMaps: [
            ctx.common.contextualErrorMap, // contextual error map is first priority
            ctx.schemaErrorMap, // then schema-bound map if available
            overrideMap, // then global override map
            overrideMap === en_js_1.default ? undefined : en_js_1.default, // then global default map
        ].filter((/**
         * @param {(undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})} x
         * @return {boolean}
         */
        (x) => !!x)),
    });
    ctx.common.issues.push(issue);
}
exports.addIssueToContext = addIssueToContext;
/** @typedef {{key: ({status: string, value: ?}|{status: string}), value: ({status: string, value: ?}|{status: string})}} */
exports.ObjectPair;
class ParseStatus {
    constructor() {
        this.value = "valid";
    }
    /**
     * @public
     * @return {void}
     */
    dirty() {
        if (this.value === "valid")
            this.value = "dirty";
    }
    /**
     * @public
     * @return {void}
     */
    abort() {
        if (this.value !== "aborted")
            this.value = "aborted";
    }
    /**
     * @public
     * @param {!ParseStatus} status
     * @param {!Array<({status: string, value: ?}|{status: string})>} results
     * @return {({status: string, value: ?}|{status: string})}
     */
    static mergeArray(status, results) {
        /** @type {!Array<?>} */
        const arrayValue = [];
        for (const s of results) {
            if (s.status === "aborted")
                return exports.INVALID;
            if ((/** @type {{status: string, value: ?}} */ (s)).status === "dirty")
                status.dirty();
            arrayValue.push((/** @type {{status: string, value: ?}} */ (s)).value);
        }
        return { status: status.value, value: arrayValue };
    }
    /**
     * @public
     * @param {!ParseStatus} status
     * @param {!Array<{key: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), value: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}>} pairs
     * @return {!Promise<({status: string, value: ?}|{status: string})>}
     */
    static async mergeObjectAsync(status, pairs) {
        /** @type {!Array<{key: ({status: string, value: ?}|{status: string}), value: ({status: string, value: ?}|{status: string})}>} */
        const syncPairs = [];
        for (const pair of pairs) {
            /** @type {({status: string, value: ?}|{status: string})} */
            const key = await pair.key;
            /** @type {({status: string, value: ?}|{status: string})} */
            const value = await pair.value;
            syncPairs.push({
                key,
                value,
            });
        }
        return ParseStatus.mergeObjectSync(status, syncPairs);
    }
    /**
     * @public
     * @param {!ParseStatus} status
     * @param {!Array<{key: ({status: string, value: ?}|{status: string}), value: ({status: string, value: ?}|{status: string}), alwaysSet: (undefined|boolean)}>} pairs
     * @return {({status: string, value: ?}|{status: string})}
     */
    static mergeObjectSync(status, pairs) {
        /** @type {?} */
        const finalObject = {};
        for (const pair of pairs) {
            const { key, value } = pair;
            if (key.status === "aborted")
                return exports.INVALID;
            if (value.status === "aborted")
                return exports.INVALID;
            if ((/** @type {{status: string, value: ?}} */ (key)).status === "dirty")
                status.dirty();
            if ((/** @type {{status: string, value: ?}} */ (value)).status === "dirty")
                status.dirty();
            if ((/** @type {{status: string, value: ?}} */ (key)).value !== "__proto__" && (typeof (/** @type {{status: string, value: ?}} */ (value)).value !== "undefined" || pair.alwaysSet)) {
                finalObject[(/** @type {{status: string, value: ?}} */ (key)).value] = (/** @type {{status: string, value: ?}} */ (value)).value;
            }
        }
        return { status: status.value, value: finalObject };
    }
}
exports.ParseStatus = ParseStatus;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ParseStatus.prototype.value;
}
/**
 * @record
 */
function ParseResult() { }
exports.ParseResult = ParseResult;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    ParseResult.prototype.status;
    /**
     * @type {?}
     * @public
     */
    ParseResult.prototype.data;
}
/** @type {{status: string}} */
exports.INVALID = Object.freeze({
    status: "aborted",
});
/** @type {function(?): {status: string, value: ?}} */
exports.DIRTY = (/**
 * @template T
 * @param {?} value
 * @return {{status: string, value: ?}}
 */
(value) => ({ status: "dirty", value }));
/** @type {function(?): {status: string, value: ?}} */
exports.OK = (/**
 * @template T
 * @param {?} value
 * @return {{status: string, value: ?}}
 */
(value) => ({ status: "valid", value }));
/** @typedef {({status: string, value: ?}|{status: string})} */
exports.SyncParseReturnType;
/** @typedef {!Promise<({status: string, value: ?}|{status: string})>} */
exports.AsyncParseReturnType;
/** @typedef {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} */
exports.ParseReturnType;
/** @type {function((!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})): boolean} */
exports.isAborted = (/**
 * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} x
 * @return {boolean}
 */
(x) => ((/** @type {?} */ (x))).status === "aborted");
/** @type {function((!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})): boolean} */
exports.isDirty = (/**
 * @template T
 * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} x
 * @return {boolean}
 */
(x) => ((/** @type {?} */ (x))).status === "dirty");
/** @type {function((!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})): boolean} */
exports.isValid = (/**
 * @template T
 * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} x
 * @return {boolean}
 */
(x) => ((/** @type {?} */ (x))).status === "valid");
/** @type {function((!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})): boolean} */
exports.isAsync = (/**
 * @template T
 * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} x
 * @return {boolean}
 */
(x) => typeof Promise !== "undefined" && x instanceof Promise);

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/typeAliases.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.typeAliases');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/typeAliases.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/** @typedef {(undefined|null|string|number|bigint|symbol|boolean)} */
exports.Primitive;
/** @typedef {(undefined|null|string|number|bigint|symbol|boolean|!Array<(undefined|null|string|number|bigint|symbol|boolean)>)} */
exports.Scalars;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/errorUtil.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.errorUtil');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/helpers/errorUtil.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
var errorUtil;
(function (errorUtil) {
    /** @typedef {(string|?)} */
    exports.ErrMessage;
    /** @type {?} */
    errorUtil.errToObj = (/**
     * @param {(undefined|string|?)=} message
     * @return {?}
     */
    (message) => typeof message === "string" ? { message } : message || {});
    // biome-ignore lint:
    /** @type {?} */
    errorUtil.toString = (/**
     * @param {(undefined|string|?)=} message
     * @return {(undefined|string)}
     */
    (message) => typeof message === "string" ? message : message?.message);
})(errorUtil || (errorUtil = {}));
exports.errorUtil = errorUtil;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/types.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.types');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/types.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_ZodError_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError");
const tsickle_errors_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors");
const tsickle_enumUtil_3 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.enumUtil");
const tsickle_errorUtil_4 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.errorUtil");
const tsickle_parseUtil_5 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.parseUtil");
const tsickle_partialUtil_6 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.partialUtil");
const tsickle_typeAliases_7 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.typeAliases");
const tsickle_util_8 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util");
const tsickle_standard_schema_9 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.standard$2dschema");
const ZodError_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError');
const errors_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors');
const errorUtil_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.errorUtil');
const parseUtil_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.parseUtil');
const util_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util');
/**
 * @record
 */
function RefinementCtx() { }
exports.RefinementCtx = RefinementCtx;
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?): void}
     * @public
     */
    RefinementCtx.prototype.addIssue;
    /**
     * @type {!Array<(string|number)>}
     * @public
     */
    RefinementCtx.prototype.path;
}
/** @typedef {!Object<string,!ZodType<?, ?, ?>>} */
exports.ZodRawShape;
/** @typedef {!ZodType<?, ?, ?>} */
exports.ZodTypeAny;
/** @typedef {?} */
exports.TypeOf;
/** @typedef {?} */
exports.input;
/** @typedef {?} */
exports.output;
/** @typedef {!TypeOf} */
exports.infer; // type-only export
/** @typedef {?} */
exports.CustomErrorParams;
/**
 * @record
 */
function ZodTypeDef() { }
exports.ZodTypeDef = ZodTypeDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})}
     * @public
     */
    ZodTypeDef.prototype.errorMap;
    /**
     * @type {(undefined|string)}
     * @public
     */
    ZodTypeDef.prototype.description;
}
/**
 * tsickle: dropped implements: dropped implements of a type literal: ParseInput
 */
class ParseInputLazyPath {
    /**
     * @public
     * @param {!tsickle_parseUtil_5.ParseContext} parent
     * @param {?} value
     * @param {!Array<(string|number)>} path
     * @param {(string|number|!Array<(string|number)>)} key
     */
    constructor(parent, value, path, key) {
        this._cachedPath = [];
        this.parent = parent;
        this.data = value;
        this._path = path;
        this._key = key;
    }
    /**
     * @public
     * @return {!Array<(string|number)>}
     */
    get path() {
        if (!this._cachedPath.length) {
            if (Array.isArray(this._key)) {
                this._cachedPath.push(...this._path, ...this._key);
            }
            else {
                this._cachedPath.push(...this._path, this._key);
            }
        }
        return this._cachedPath;
    }
}
/* istanbul ignore if */
if (false) {
    /**
     * @type {!tsickle_parseUtil_5.ParseContext}
     * @public
     */
    ParseInputLazyPath.prototype.parent;
    /**
     * @type {?}
     * @public
     */
    ParseInputLazyPath.prototype.data;
    /**
     * @type {!Array<(string|number)>}
     * @public
     */
    ParseInputLazyPath.prototype._path;
    /**
     * @type {(string|number|!Array<(string|number)>)}
     * @public
     */
    ParseInputLazyPath.prototype._key;
    /**
     * @type {!Array<(string|number)>}
     * @public
     */
    ParseInputLazyPath.prototype._cachedPath;
}
/** @type {function(!tsickle_parseUtil_5.ParseContext, ({status: string, value: ?}|{status: string})): ({success: boolean, data: ?}|{success: boolean, error: !tsickle_ZodError_1.ZodError<?>})} */
const handleResult = (/**
 * @template Input, Output
 * @param {!tsickle_parseUtil_5.ParseContext} ctx
 * @param {({status: string, value: ?}|{status: string})} result
 * @return {({success: boolean, data: ?}|{success: boolean, error: !tsickle_ZodError_1.ZodError<?>})}
 */
(ctx, result) => {
    if ((0, parseUtil_js_1.isValid)(result)) {
        return { success: true, data: (/** @type {{status: string, value: ?}} */ (result)).value };
    }
    else {
        if (!ctx.common.issues.length) {
            throw new Error("Validation failed but no issues detected.");
        }
        return {
            success: false,
            /**
             * @public
             * @return {?}
             */
            get error() {
                if (((/** @type {?} */ (this)))._error)
                    return (/** @type {!Error} */ (((/** @type {?} */ (this)))._error));
                /** @type {!tsickle_ZodError_1.ZodError<?>} */
                const error = new ZodError_js_1.ZodError(ctx.common.issues);
                ((/** @type {?} */ (this)))._error = error;
                return ((/** @type {?} */ (this)))._error;
            },
        };
    }
});
/** @typedef {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})} */
exports.RawCreateParams;
/** @typedef {{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), description: (undefined|string)}} */
exports.ProcessedCreateParams;
/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})} params
 * @return {{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), description: (undefined|string)}}
 */
function processCreateParams(params) {
    if (!params)
        return {};
    const { errorMap, invalid_type_error, required_error, description } = params;
    if (errorMap && (invalid_type_error || required_error)) {
        throw new Error(`Can't use "invalid_type_error" or "required_error" in conjunction with custom error map.`);
    }
    if (errorMap)
        return { errorMap: errorMap, description };
    /** @type {function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}} */
    const customMap = (/**
     * @param {(!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue)} iss
     * @param {{defaultError: string, data: ?}} ctx
     * @return {{message: string}}
     */
    (iss, ctx) => {
        const { message } = params;
        if (iss.code === "invalid_enum_value") {
            return { message: message ?? ctx.defaultError };
        }
        if (typeof ctx.data === "undefined") {
            return { message: message ?? required_error ?? ctx.defaultError };
        }
        if ((/** @type {(!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue)} */ (iss)).code !== "invalid_type")
            return { message: ctx.defaultError };
        return { message: message ?? invalid_type_error ?? ctx.defaultError };
    });
    return { errorMap: customMap, description };
}
/** @typedef {{success: boolean, data: ?, error: undefined}} */
exports.SafeParseSuccess;
/** @typedef {{success: boolean, error: !tsickle_ZodError_1.ZodError<?>, data: undefined}} */
exports.SafeParseError;
/** @typedef {({success: boolean, error: !tsickle_ZodError_1.ZodError<?>, data: undefined}|{success: boolean, data: ?, error: undefined})} */
exports.SafeParseReturnType;
/**
 * @abstract
 * @template Output, Def, Input
 */
class ZodType {
    /**
     * @public
     * @return {(undefined|string)}
     */
    get description() {
        return this._def.description;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {string}
     */
    _getType(input) {
        return (0, util_js_1.getParsedType)(input.data);
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @param {(undefined|!tsickle_parseUtil_5.ParseContext)=} ctx
     * @return {!tsickle_parseUtil_5.ParseContext}
     */
    _getOrReturnCtx(input, ctx) {
        return (ctx || {
            common: input.parent.common,
            data: input.data,
            parsedType: (0, util_js_1.getParsedType)(input.data),
            schemaErrorMap: this._def.errorMap,
            path: input.path,
            parent: input.parent,
        });
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {{status: !tsickle_parseUtil_5.ParseStatus, ctx: !tsickle_parseUtil_5.ParseContext}}
     */
    _processInputParams(input) {
        return {
            status: new parseUtil_js_1.ParseStatus(),
            ctx: {
                common: input.parent.common,
                data: input.data,
                parsedType: (0, util_js_1.getParsedType)(input.data),
                schemaErrorMap: this._def.errorMap,
                path: input.path,
                parent: input.parent,
            },
        };
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {({status: string, value: Output}|{status: string})}
     */
    _parseSync(input) {
        /** @type {(!Promise<({status: string, value: Output}|{status: string})>|{status: string, value: Output}|{status: string})} */
        const result = this._parse(input);
        if ((0, parseUtil_js_1.isAsync)(result)) {
            throw new Error("Synchronous parse encountered promise.");
        }
        return result;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {!Promise<({status: string, value: Output}|{status: string})>}
     */
    _parseAsync(input) {
        /** @type {(!Promise<({status: string, value: Output}|{status: string})>|{status: string, value: Output}|{status: string})} */
        const result = this._parse(input);
        return Promise.resolve(result);
    }
    /**
     * @public
     * @param {*} data
     * @param {(undefined|?)=} params
     * @return {Output}
     */
    parse(data, params) {
        /** @type {({success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}|{success: boolean, data: Output, error: undefined})} */
        const result = this.safeParse(data, params);
        if (result.success)
            return (/** @type {{success: boolean, data: Output, error: undefined}} */ (result)).data;
        throw (/** @type {{success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}} */ (result)).error;
    }
    /**
     * @public
     * @param {*} data
     * @param {(undefined|?)=} params
     * @return {({success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}|{success: boolean, data: Output, error: undefined})}
     */
    safeParse(data, params) {
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = {
            common: {
                issues: [],
                async: params?.async ?? false,
                contextualErrorMap: params?.errorMap,
            },
            path: params?.path || [],
            schemaErrorMap: this._def.errorMap,
            parent: null,
            data,
            parsedType: (0, util_js_1.getParsedType)(data),
        };
        /** @type {({status: string, value: Output}|{status: string})} */
        const result = this._parseSync({ data, path: ctx.path, parent: ctx });
        return handleResult(ctx, result);
    }
    /**
     * @public
     * @param {*} data
     * @return {(!tsickle_standard_schema_9.StandardSchemaV1.FailureResult|!Promise<(!tsickle_standard_schema_9.StandardSchemaV1.FailureResult|!tsickle_standard_schema_9.StandardSchemaV1.SuccessResult<Output>)>|!tsickle_standard_schema_9.StandardSchemaV1.SuccessResult<Output>)}
     */
    "~validate"(data) {
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = {
            common: {
                issues: [],
                async: !!((/** @type {?} */ (this["~standard"]))).async,
            },
            path: [],
            schemaErrorMap: this._def.errorMap,
            parent: null,
            data,
            parsedType: (0, util_js_1.getParsedType)(data),
        };
        if (!((/** @type {?} */ (this["~standard"]))).async) {
            try {
                /** @type {({status: string, value: Output}|{status: string})} */
                const result = this._parseSync({ data, path: [], parent: ctx });
                return (0, parseUtil_js_1.isValid)(result)
                    ? {
                        value: (/** @type {{status: string, value: Output}} */ (result)).value,
                    }
                    : {
                        issues: ctx.common.issues,
                    };
            }
            catch (err) {
                if (((/** @type {!Error} */ (err)))?.message?.toLowerCase()?.includes("encountered")) {
                    ((/** @type {?} */ (this["~standard"]))).async = true;
                }
                ((/** @type {?} */ (ctx))).common = {
                    issues: [],
                    async: true,
                };
            }
        }
        return this._parseAsync({ data, path: [], parent: ctx }).then((/**
         * @param {({status: string, value: Output}|{status: string})} result
         * @return {({value: Output, issues: undefined}|{value: undefined, issues: !Array<?>})}
         */
        (result) => (0, parseUtil_js_1.isValid)(result)
            ? {
                value: (/** @type {{status: string, value: Output}} */ (result)).value,
            }
            : {
                issues: ctx.common.issues,
            }));
    }
    /**
     * @public
     * @param {*} data
     * @param {(undefined|?)=} params
     * @return {!Promise<Output>}
     */
    async parseAsync(data, params) {
        /** @type {({success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}|{success: boolean, data: Output, error: undefined})} */
        const result = await this.safeParseAsync(data, params);
        if (result.success)
            return (/** @type {{success: boolean, data: Output, error: undefined}} */ (result)).data;
        throw (/** @type {{success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}} */ (result)).error;
    }
    /**
     * @public
     * @param {*} data
     * @param {(undefined|?)=} params
     * @return {!Promise<({success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}|{success: boolean, data: Output, error: undefined})>}
     */
    async safeParseAsync(data, params) {
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = {
            common: {
                issues: [],
                contextualErrorMap: params?.errorMap,
                async: true,
            },
            path: params?.path || [],
            schemaErrorMap: this._def.errorMap,
            parent: null,
            data,
            parsedType: (0, util_js_1.getParsedType)(data),
        };
        /** @type {(!Promise<({status: string, value: Output}|{status: string})>|{status: string, value: Output}|{status: string})} */
        const maybeAsyncResult = this._parse({ data, path: ctx.path, parent: ctx });
        /** @type {({status: string, value: Output}|{status: string})} */
        const result = await ((0, parseUtil_js_1.isAsync)(maybeAsyncResult) ? maybeAsyncResult : Promise.resolve(maybeAsyncResult));
        return handleResult(ctx, result);
    }
    /**
     * @public
     * @param {function(Output): *} check
     * @param {(undefined|string|?|function(Output): ?)=} message
     * @return {!ZodEffects<!ZodType, Output, Input>}
     */
    refine(check, message) {
        /** @type {function(Output): ?} */
        const getIssueProperties = (/**
         * @param {Output} val
         * @return {?}
         */
        (val) => {
            if (typeof message === "string" || typeof message === "undefined") {
                return { message };
            }
            else if (typeof message === "function") {
                return message(val);
            }
            else {
                return message;
            }
        });
        return this._refinement((/**
         * @param {Output} val
         * @param {!RefinementCtx} ctx
         * @return {(boolean|!Promise<boolean>)}
         */
        (val, ctx) => {
            /** @type {*} */
            const result = check(val);
            /** @type {function(): void} */
            const setError = (/**
             * @return {void}
             */
            () => ctx.addIssue({
                code: ZodError_js_1.ZodIssueCode.custom,
                ...getIssueProperties(val),
            }));
            if (typeof Promise !== "undefined" && result instanceof Promise) {
                return (/** @type {!Promise<?>} */ (result)).then((/**
                 * @param {?} data
                 * @return {boolean}
                 */
                (data) => {
                    if (!data) {
                        setError();
                        return false;
                    }
                    else {
                        return true;
                    }
                }));
            }
            if (!result) {
                setError();
                return false;
            }
            else {
                return true;
            }
        }));
    }
    /**
     * @public
     * @param {function(Output): *} check
     * @param {(function(Output, !RefinementCtx): ?|?)} refinementData
     * @return {!ZodEffects<!ZodType, Output, Input>}
     */
    refinement(check, refinementData) {
        return this._refinement((/**
         * @param {Output} val
         * @param {!RefinementCtx} ctx
         * @return {boolean}
         */
        (val, ctx) => {
            if (!check(val)) {
                ctx.addIssue(typeof refinementData === "function" ? refinementData(val, ctx) : refinementData);
                return false;
            }
            else {
                return true;
            }
        }));
    }
    /**
     * @public
     * @param {function(Output, !RefinementCtx): ?} refinement
     * @return {!ZodEffects<!ZodType, Output, Input>}
     */
    _refinement(refinement) {
        return new ZodEffects({
            schema: this,
            typeName: ZodFirstPartyTypeKind.ZodEffects,
            effect: { type: "refinement", refinement },
        });
    }
    /**
     * @public
     * @param {function(Output, !RefinementCtx): *} refinement
     * @return {!ZodEffects<!ZodType, Output, Input>}
     */
    superRefine(refinement) {
        return this._refinement(refinement);
    }
    /**
     * @public
     * @param {Def} def
     */
    constructor(def) {
        /**
         * Alias of safeParseAsync
         */
        this.spa = this.safeParseAsync;
        this._def = def;
        this.parse = this.parse.bind(this);
        this.safeParse = this.safeParse.bind(this);
        this.parseAsync = this.parseAsync.bind(this);
        this.safeParseAsync = this.safeParseAsync.bind(this);
        this.spa = this.spa.bind(this);
        this.refine = this.refine.bind(this);
        this.refinement = this.refinement.bind(this);
        this.superRefine = this.superRefine.bind(this);
        this.optional = this.optional.bind(this);
        this.nullable = this.nullable.bind(this);
        this.nullish = this.nullish.bind(this);
        this.array = this.array.bind(this);
        this.promise = this.promise.bind(this);
        this.or = this.or.bind(this);
        this.and = this.and.bind(this);
        this.transform = this.transform.bind(this);
        this.brand = this.brand.bind(this);
        this.default = this.default.bind(this);
        this.catch = this.catch.bind(this);
        this.describe = this.describe.bind(this);
        this.pipe = this.pipe.bind(this);
        this.readonly = this.readonly.bind(this);
        this.isNullable = this.isNullable.bind(this);
        this.isOptional = this.isOptional.bind(this);
        this["~standard"] = {
            version: 1,
            vendor: "zod",
            validate: (/**
             * @param {*} data
             * @return {(!tsickle_standard_schema_9.StandardSchemaV1.FailureResult|!Promise<(!tsickle_standard_schema_9.StandardSchemaV1.FailureResult|!tsickle_standard_schema_9.StandardSchemaV1.SuccessResult<Output>)>|!tsickle_standard_schema_9.StandardSchemaV1.SuccessResult<Output>)}
             */
            (data) => this["~validate"](data)),
        };
    }
    /**
     * @public
     * @return {!ZodOptional<!ZodType>}
     */
    optional() {
        return (/** @type {?} */ (ZodOptional.create(this, this._def)));
    }
    /**
     * @public
     * @return {!ZodNullable<!ZodType>}
     */
    nullable() {
        return (/** @type {?} */ (ZodNullable.create(this, this._def)));
    }
    /**
     * @public
     * @return {!ZodOptional<!ZodNullable<!ZodType>>}
     */
    nullish() {
        return this.nullable().optional();
    }
    /**
     * @public
     * @return {!ZodArray<!ZodType, string>}
     */
    array() {
        return ZodArray.create(this);
    }
    /**
     * @public
     * @return {!ZodPromise<!ZodType>}
     */
    promise() {
        return ZodPromise.create(this, this._def);
    }
    /**
     * @public
     * @template T
     * @param {T} option
     * @return {!ZodUnion<!Array<?>>}
     */
    or(option) {
        return (/** @type {?} */ (ZodUnion.create([this, option], this._def)));
    }
    /**
     * @public
     * @template T
     * @param {T} incoming
     * @return {!ZodIntersection<!ZodType, T>}
     */
    and(incoming) {
        return ZodIntersection.create(this, incoming, this._def);
    }
    /**
     * @public
     * @template NewOut
     * @param {function(Output, !RefinementCtx): (NewOut|!Promise<NewOut>)} transform
     * @return {!ZodEffects<!ZodType, NewOut, ?>}
     */
    transform(transform) {
        return (/** @type {?} */ (new ZodEffects({
            ...processCreateParams(this._def),
            schema: this,
            typeName: ZodFirstPartyTypeKind.ZodEffects,
            effect: { type: "transform", transform },
        })));
    }
    /**
     * @public
     * @param {?} def
     * @return {?}
     */
    default(def) {
        /** @type {?} */
        const defaultValueFunc = typeof def === "function" ? def : (/**
         * @return {?}
         */
        () => def);
        return (/** @type {?} */ (new ZodDefault({
            ...processCreateParams(this._def),
            innerType: this,
            defaultValue: defaultValueFunc,
            typeName: ZodFirstPartyTypeKind.ZodDefault,
        })));
    }
    /**
     * @public
     * @template B
     * @return {!ZodBranded<!ZodType, B>}
     */
    brand() {
        return new ZodBranded({
            typeName: ZodFirstPartyTypeKind.ZodBranded,
            type: this,
            ...processCreateParams(this._def),
        });
    }
    /**
     * @public
     * @param {?} def
     * @return {?}
     */
    catch(def) {
        /** @type {?} */
        const catchValueFunc = typeof def === "function" ? def : (/**
         * @return {?}
         */
        () => def);
        return (/** @type {?} */ (new ZodCatch({
            ...processCreateParams(this._def),
            innerType: this,
            catchValue: catchValueFunc,
            typeName: ZodFirstPartyTypeKind.ZodCatch,
        })));
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {string} description
     * @return {THIS}
     */
    describe(description) {
        /** @type {?} */
        const This = ((/** @type {?} */ ((/** @type {!ZodType} */ (this))))).constructor;
        return new This({
            ...(/** @type {!ZodType} */ (this))._def,
            description,
        });
    }
    /**
     * @public
     * @template T
     * @param {T} target
     * @return {!ZodPipeline<!ZodType, T>}
     */
    pipe(target) {
        return ZodPipeline.create(this, target);
    }
    /**
     * @public
     * @return {!ZodReadonly<!ZodType>}
     */
    readonly() {
        return ZodReadonly.create(this);
    }
    /**
     * @public
     * @return {boolean}
     */
    isOptional() {
        return this.safeParse(undefined).success;
    }
    /**
     * @public
     * @return {boolean}
     */
    isNullable() {
        return this.safeParse(null).success;
    }
}
exports.ZodType = ZodType;
exports.Schema = ZodType;
exports.ZodSchema = ZodType;
/* istanbul ignore if */
if (false) {
    /**
     * @const {Output}
     * @public
     */
    ZodType.prototype._type;
    /**
     * @const {Output}
     * @public
     */
    ZodType.prototype._output;
    /**
     * @const {Input}
     * @public
     */
    ZodType.prototype._input;
    /**
     * @const {Def}
     * @public
     */
    ZodType.prototype._def;
    /* Skipping unnamed member:
    "~standard": StandardSchemaV1.Props<Input, Output>;*/
    /**
     * Alias of safeParseAsync
     * @type {function(*, (undefined|?)=): !Promise<({success: boolean, error: !tsickle_ZodError_1.ZodError<Input>, data: undefined}|{success: boolean, data: Output, error: undefined})>}
     * @public
     */
    ZodType.prototype.spa;
    /**
     * @abstract
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: Output}|{status: string})>|{status: string, value: Output}|{status: string})}
     */
    ZodType.prototype._parse = function (input) { };
}
/** @typedef {string} */
exports.IpVersion;
/** @typedef {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */
exports.ZodStringCheck;
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodStringDef() { }
exports.ZodStringDef = ZodStringDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!Array<({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})>}
     * @public
     */
    ZodStringDef.prototype.checks;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodStringDef.prototype.typeName;
    /**
     * @type {boolean}
     * @public
     */
    ZodStringDef.prototype.coerce;
}
/** @type {!RegExp} */
const cuidRegex = /^c[^\s-]{8,}$/i;
/** @type {!RegExp} */
const cuid2Regex = /^[0-9a-z]+$/;
/** @type {!RegExp} */
const ulidRegex = /^[0-9A-HJKMNP-TV-Z]{26}$/i;
// const uuidRegex =
//   /^([a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}|00000000-0000-0000-0000-000000000000)$/i;
/** @type {!RegExp} */
const uuidRegex = /^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$/i;
/** @type {!RegExp} */
const nanoidRegex = /^[a-z0-9_-]{21}$/i;
/** @type {!RegExp} */
const jwtRegex = /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$/;
/** @type {!RegExp} */
const durationRegex = /^[-+]?P(?!$)(?:(?:[-+]?\d+Y)|(?:[-+]?\d+[.,]\d+Y$))?(?:(?:[-+]?\d+M)|(?:[-+]?\d+[.,]\d+M$))?(?:(?:[-+]?\d+W)|(?:[-+]?\d+[.,]\d+W$))?(?:(?:[-+]?\d+D)|(?:[-+]?\d+[.,]\d+D$))?(?:T(?=[\d+-])(?:(?:[-+]?\d+H)|(?:[-+]?\d+[.,]\d+H$))?(?:(?:[-+]?\d+M)|(?:[-+]?\d+[.,]\d+M$))?(?:[-+]?\d+(?:[.,]\d+)?S)?)??$/;
// from https://stackoverflow.com/a/46181/1550155
// old version: too slow, didn't support unicode
// const emailRegex = /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))$/i;
//old email regex
// const emailRegex = /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@((?!-)([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{1,})[^-<>()[\].,;:\s@"]$/i;
// eslint-disable-next-line
// const emailRegex =
//   /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[(((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2}))\.){3}((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2}))\])|(\[IPv6:(([a-f0-9]{1,4}:){7}|::([a-f0-9]{1,4}:){0,6}|([a-f0-9]{1,4}:){1}:([a-f0-9]{1,4}:){0,5}|([a-f0-9]{1,4}:){2}:([a-f0-9]{1,4}:){0,4}|([a-f0-9]{1,4}:){3}:([a-f0-9]{1,4}:){0,3}|([a-f0-9]{1,4}:){4}:([a-f0-9]{1,4}:){0,2}|([a-f0-9]{1,4}:){5}:([a-f0-9]{1,4}:){0,1})([a-f0-9]{1,4}|(((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2}))\.){3}((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2})))\])|([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])*(\.[A-Za-z]{2,})+))$/;
// const emailRegex =
//   /^[a-zA-Z0-9\.\!\#\$\%\&\'\*\+\/\=\?\^\_\`\{\|\}\~\-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
// const emailRegex =
//   /^(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])$/i;
/** @type {!RegExp} */
const emailRegex = /^(?!\.)(?!.*\.\.)([A-Z0-9_'+\-\.]*)[A-Z0-9_+-]@([A-Z0-9][A-Z0-9\-]*\.)+[A-Z]{2,}$/i;
// const emailRegex =
//   /^[a-z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9\-]+)*$/i;
// from https://thekevinscott.com/emojis-in-javascript/#writing-a-regular-expression
/** @type {string} */
const _emojiRegex = `^(\\p{Extended_Pictographic}|\\p{Emoji_Component})+$`;
/** @type {!RegExp} */
let emojiRegex;
// faster, simpler, safer
/** @type {!RegExp} */
const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$/;
/** @type {!RegExp} */
const ipv4CidrRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\/(3[0-2]|[12]?[0-9])$/;
// const ipv6Regex =
// /^(([a-f0-9]{1,4}:){7}|::([a-f0-9]{1,4}:){0,6}|([a-f0-9]{1,4}:){1}:([a-f0-9]{1,4}:){0,5}|([a-f0-9]{1,4}:){2}:([a-f0-9]{1,4}:){0,4}|([a-f0-9]{1,4}:){3}:([a-f0-9]{1,4}:){0,3}|([a-f0-9]{1,4}:){4}:([a-f0-9]{1,4}:){0,2}|([a-f0-9]{1,4}:){5}:([a-f0-9]{1,4}:){0,1})([a-f0-9]{1,4}|(((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2}))\.){3}((25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([0-9]{1,2})))$/;
/** @type {!RegExp} */
const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/;
/** @type {!RegExp} */
const ipv6CidrRegex = /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))\/(12[0-8]|1[01][0-9]|[1-9]?[0-9])$/;
// https://stackoverflow.com/questions/7860392/determine-if-string-is-in-base64-using-javascript
/** @type {!RegExp} */
const base64Regex = /^([0-9a-zA-Z+/]{4})*(([0-9a-zA-Z+/]{2}==)|([0-9a-zA-Z+/]{3}=))?$/;
// https://base64.guru/standards/base64url
/** @type {!RegExp} */
const base64urlRegex = /^([0-9a-zA-Z-_]{4})*(([0-9a-zA-Z-_]{2}(==)?)|([0-9a-zA-Z-_]{3}(=)?))?$/;
// simple
// const dateRegexSource = `\\d{4}-\\d{2}-\\d{2}`;
// no leap year validation
// const dateRegexSource = `\\d{4}-((0[13578]|10|12)-31|(0[13-9]|1[0-2])-30|(0[1-9]|1[0-2])-(0[1-9]|1\\d|2\\d))`;
// with leap year validation
/** @type {string} */
const dateRegexSource = `((\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-((0[13578]|1[02])-(0[1-9]|[12]\\d|3[01])|(0[469]|11)-(0[1-9]|[12]\\d|30)|(02)-(0[1-9]|1\\d|2[0-8])))`;
/** @type {!RegExp} */
const dateRegex = new RegExp(`^${dateRegexSource}$`);
/**
 * @param {{precision: (undefined|null|number)}} args
 * @return {string}
 */
function timeRegexSource(args) {
    /** @type {string} */
    let secondsRegexSource = `[0-5]\\d`;
    if (args.precision) {
        secondsRegexSource = `${secondsRegexSource}\\.\\d{${args.precision}}`;
    }
    else if (args.precision == null) {
        secondsRegexSource = `${secondsRegexSource}(\\.\\d+)?`;
    }
    /** @type {string} */
    const secondsQuantifier = args.precision ? "+" : "?";
    return `([01]\\d|2[0-3]):[0-5]\\d(:${secondsRegexSource})${secondsQuantifier}`;
}
/**
 * @param {{offset: (undefined|boolean), local: (undefined|boolean), precision: (undefined|null|number)}} args
 * @return {!RegExp}
 */
function timeRegex(args) {
    return new RegExp(`^${timeRegexSource(args)}$`);
}
// Adapted from https://stackoverflow.com/a/3143231
/**
 * @param {{precision: (undefined|null|number), offset: (undefined|boolean), local: (undefined|boolean)}} args
 * @return {!RegExp}
 */
function datetimeRegex(args) {
    /** @type {string} */
    let regex = `${dateRegexSource}T${timeRegexSource(args)}`;
    /** @type {!Array<string>} */
    const opts = [];
    opts.push(args.local ? `Z?` : `Z`);
    if (args.offset)
        opts.push(`([+-]\\d{2}:?\\d{2})`);
    regex = `${regex}(${opts.join("|")})`;
    return new RegExp(`^${regex}$`);
}
exports.datetimeRegex = datetimeRegex;
/**
 * @param {string} ip
 * @param {(undefined|string)=} version
 * @return {boolean}
 */
function isValidIP(ip, version) {
    if ((version === "v4" || !version) && ipv4Regex.test(ip)) {
        return true;
    }
    if ((version === "v6" || !version) && ipv6Regex.test(ip)) {
        return true;
    }
    return false;
}
/**
 * @param {string} jwt
 * @param {(undefined|string)=} alg
 * @return {boolean}
 */
function isValidJWT(jwt, alg) {
    if (!jwtRegex.test(jwt))
        return false;
    try {
        const [header__tsickle_destructured_1] = jwt.split(".");
        const header = /** @type {string} */ (header__tsickle_destructured_1);
        if (!header)
            return false;
        // Convert base64url to base64
        /** @type {string} */
        const base64 = header
            .replace(/-/g, "+")
            .replace(/_/g, "/")
            .padEnd(header.length + ((4 - (header.length % 4)) % 4), "=");
        /** @type {?} */
        const decoded = JSON.parse(atob(base64));
        if (typeof decoded !== "object" || decoded === null)
            return false;
        if ("typ" in decoded && decoded?.typ !== "JWT")
            return false;
        if (!decoded.alg)
            return false;
        if (alg && decoded.alg !== alg)
            return false;
        return true;
    }
    catch {
        return false;
    }
}
/**
 * @param {string} ip
 * @param {(undefined|string)=} version
 * @return {boolean}
 */
function isValidCidr(ip, version) {
    if ((version === "v4" || !version) && ipv4CidrRegex.test(ip)) {
        return true;
    }
    if ((version === "v6" || !version) && ipv6CidrRegex.test(ip)) {
        return true;
    }
    return false;
}
/**
 * @extends {ZodType<string, !ZodStringDef, string>}
 */
class ZodString extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: string}|{status: string})>|{status: string, value: string}|{status: string})}
     */
    _parse(input) {
        if (this._def.coerce) {
            input.data = String(input.data);
        }
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.string) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.string,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {!tsickle_parseUtil_5.ParseStatus} */
        const status = new parseUtil_js_1.ParseStatus();
        /** @type {(undefined|!tsickle_parseUtil_5.ParseContext)} */
        let ctx = undefined;
        for (const check of this._def.checks) {
            if (check.kind === "min") {
                if (input.data.length < (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_small,
                        minimum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                        type: "string",
                        inclusive: true,
                        exact: false,
                        message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "max") {
                if (input.data.length > (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_big,
                        maximum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                        type: "string",
                        inclusive: true,
                        exact: false,
                        message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "length") {
                /** @type {boolean} */
                const tooBig = input.data.length > (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value;
                /** @type {boolean} */
                const tooSmall = input.data.length < (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value;
                if (tooBig || tooSmall) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    if (tooBig) {
                        (0, parseUtil_js_1.addIssueToContext)(ctx, {
                            code: ZodError_js_1.ZodIssueCode.too_big,
                            maximum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                            type: "string",
                            inclusive: true,
                            exact: true,
                            message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                        });
                    }
                    else if (tooSmall) {
                        (0, parseUtil_js_1.addIssueToContext)(ctx, {
                            code: ZodError_js_1.ZodIssueCode.too_small,
                            minimum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                            type: "string",
                            inclusive: true,
                            exact: true,
                            message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                        });
                    }
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "email") {
                if (!emailRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "email",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "emoji") {
                if (!emojiRegex) {
                    emojiRegex = new RegExp(_emojiRegex, "u");
                }
                if (!emojiRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "emoji",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "uuid") {
                if (!uuidRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "uuid",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "nanoid") {
                if (!nanoidRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "nanoid",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "cuid") {
                if (!cuidRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "cuid",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "cuid2") {
                if (!cuid2Regex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "cuid2",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "ulid") {
                if (!ulidRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "ulid",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "url") {
                try {
                    new URL(input.data);
                }
                catch {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "url",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "regex") {
                (/** @type {{kind: string, regex: !RegExp, message: (undefined|string)}} */ (check)).regex.lastIndex = 0;
                /** @type {boolean} */
                const testResult = (/** @type {{kind: string, regex: !RegExp, message: (undefined|string)}} */ (check)).regex.test(input.data);
                if (!testResult) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "regex",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, regex: !RegExp, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "trim") {
                input.data = input.data.trim();
            }
            else if ((/** @type {({kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "includes") {
                if (!((/** @type {string} */ (input.data))).includes((/** @type {{kind: string, value: string, position: (undefined|number), message: (undefined|string)}} */ (check)).value, (/** @type {{kind: string, value: string, position: (undefined|number), message: (undefined|string)}} */ (check)).position)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: { includes: (/** @type {{kind: string, value: string, position: (undefined|number), message: (undefined|string)}} */ (check)).value, position: (/** @type {{kind: string, value: string, position: (undefined|number), message: (undefined|string)}} */ (check)).position },
                        message: (/** @type {{kind: string, value: string, position: (undefined|number), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: string, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "toLowerCase") {
                input.data = input.data.toLowerCase();
            }
            else if ((/** @type {({kind: string, value: string, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "toUpperCase") {
                input.data = input.data.toUpperCase();
            }
            else if ((/** @type {({kind: string, value: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "startsWith") {
                if (!((/** @type {string} */ (input.data))).startsWith((/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).value)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: { startsWith: (/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).value },
                        message: (/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: string, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "endsWith") {
                if (!((/** @type {string} */ (input.data))).endsWith((/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).value)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: { endsWith: (/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).value },
                        message: (/** @type {{kind: string, value: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "datetime") {
                /** @type {!RegExp} */
                const regex = datetimeRegex(check);
                if (!regex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: "datetime",
                        message: (/** @type {{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "date") {
                /** @type {!RegExp} */
                const regex = dateRegex;
                if (!regex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: "date",
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "time") {
                /** @type {!RegExp} */
                const regex = timeRegex(check);
                if (!regex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        validation: "time",
                        message: (/** @type {{kind: string, precision: (null|number), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} */ (check)).kind === "duration") {
                if (!durationRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "duration",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "ip") {
                if (!isValidIP(input.data, (/** @type {{kind: string, version: (undefined|string), message: (undefined|string)}} */ (check)).version)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "ip",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, version: (undefined|string), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "jwt") {
                if (!isValidJWT(input.data, (/** @type {{kind: string, alg: (undefined|string), message: (undefined|string)}} */ (check)).alg)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "jwt",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, alg: (undefined|string), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, version: (undefined|string), message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "cidr") {
                if (!isValidCidr(input.data, (/** @type {{kind: string, version: (undefined|string), message: (undefined|string)}} */ (check)).version)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "cidr",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, version: (undefined|string), message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {{kind: string, message: (undefined|string)}} */ (check)).kind === "base64") {
                if (!base64Regex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "base64",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {{kind: string, message: (undefined|string)}} */ (check)).kind === "base64url") {
                if (!base64urlRegex.test(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        validation: "base64url",
                        code: ZodError_js_1.ZodIssueCode.invalid_string,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else {
                util_js_1.util.assertNever(check);
            }
        }
        return { status: status.value, value: input.data };
    }
    /**
     * @protected
     * @param {!RegExp} regex
     * @param {(string|{includes: string, position: (undefined|number)}|{startsWith: string}|{endsWith: string})} validation
     * @param {(undefined|string|?)=} message
     * @return {!ZodEffects<!ZodString, string, string>}
     */
    _regex(regex, validation, message) {
        return this.refinement((/**
         * @param {string} data
         * @return {boolean}
         */
        (data) => regex.test(data)), {
            validation,
            code: ZodError_js_1.ZodIssueCode.invalid_string,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} check
     * @return {!ZodString}
     */
    _addCheck(check) {
        return new ZodString({
            ...this._def,
            checks: [...this._def.checks, check],
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    email(message) {
        return this._addCheck({ kind: "email", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    url(message) {
        return this._addCheck({ kind: "url", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    emoji(message) {
        return this._addCheck({ kind: "emoji", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    uuid(message) {
        return this._addCheck({ kind: "uuid", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    nanoid(message) {
        return this._addCheck({ kind: "nanoid", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    cuid(message) {
        return this._addCheck({ kind: "cuid", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    cuid2(message) {
        return this._addCheck({ kind: "cuid2", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    ulid(message) {
        return this._addCheck({ kind: "ulid", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    base64(message) {
        return this._addCheck({ kind: "base64", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    base64url(message) {
        // base64url encoding is a modification of base64 that can safely be used in URLs and filenames
        return this._addCheck({
            kind: "base64url",
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {(undefined|{alg: (undefined|string), message: (undefined|string)})=} options
     * @return {!ZodString}
     */
    jwt(options) {
        return this._addCheck({ kind: "jwt", ...errorUtil_js_1.errorUtil.errToObj(options) });
    }
    /**
     * @public
     * @param {(undefined|string|{version: (undefined|string), message: (undefined|string)})=} options
     * @return {!ZodString}
     */
    ip(options) {
        return this._addCheck({ kind: "ip", ...errorUtil_js_1.errorUtil.errToObj(options) });
    }
    /**
     * @public
     * @param {(undefined|string|{version: (undefined|string), message: (undefined|string)})=} options
     * @return {!ZodString}
     */
    cidr(options) {
        return this._addCheck({ kind: "cidr", ...errorUtil_js_1.errorUtil.errToObj(options) });
    }
    /**
     * @public
     * @param {(undefined|string|{message: (undefined|string), precision: (undefined|null|number), offset: (undefined|boolean), local: (undefined|boolean)})=} options
     * @return {!ZodString}
     */
    datetime(options) {
        if (typeof options === "string") {
            return this._addCheck({
                kind: "datetime",
                precision: null,
                offset: false,
                local: false,
                message: options,
            });
        }
        return this._addCheck({
            kind: "datetime",
            precision: typeof options?.precision === "undefined" ? null : options?.precision,
            offset: options?.offset ?? false,
            local: options?.local ?? false,
            ...errorUtil_js_1.errorUtil.errToObj(options?.message),
        });
    }
    /**
     * @public
     * @param {(undefined|string)=} message
     * @return {!ZodString}
     */
    date(message) {
        return this._addCheck({ kind: "date", message });
    }
    /**
     * @public
     * @param {(undefined|string|{message: (undefined|string), precision: (undefined|null|number)})=} options
     * @return {!ZodString}
     */
    time(options) {
        if (typeof options === "string") {
            return this._addCheck({
                kind: "time",
                precision: null,
                message: options,
            });
        }
        return this._addCheck({
            kind: "time",
            precision: typeof options?.precision === "undefined" ? null : options?.precision,
            ...errorUtil_js_1.errorUtil.errToObj(options?.message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    duration(message) {
        return this._addCheck({ kind: "duration", ...errorUtil_js_1.errorUtil.errToObj(message) });
    }
    /**
     * @public
     * @param {!RegExp} regex
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    regex(regex, message) {
        return this._addCheck({
            kind: "regex",
            regex: regex,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {string} value
     * @param {(undefined|{message: (undefined|string), position: (undefined|number)})=} options
     * @return {!ZodString}
     */
    includes(value, options) {
        return this._addCheck({
            kind: "includes",
            value: value,
            position: options?.position,
            ...errorUtil_js_1.errorUtil.errToObj(options?.message),
        });
    }
    /**
     * @public
     * @param {string} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    startsWith(value, message) {
        return this._addCheck({
            kind: "startsWith",
            value: value,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {string} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    endsWith(value, message) {
        return this._addCheck({
            kind: "endsWith",
            value: value,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {number} minLength
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    min(minLength, message) {
        return this._addCheck({
            kind: "min",
            value: minLength,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {number} maxLength
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    max(maxLength, message) {
        return this._addCheck({
            kind: "max",
            value: maxLength,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * @public
     * @param {number} len
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    length(len, message) {
        return this._addCheck({
            kind: "length",
            value: len,
            ...errorUtil_js_1.errorUtil.errToObj(message),
        });
    }
    /**
     * Equivalent to `.min(1)`
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodString}
     */
    nonempty(message) {
        return this.min(1, errorUtil_js_1.errorUtil.errToObj(message));
    }
    /**
     * @public
     * @return {!ZodString}
     */
    trim() {
        return new ZodString({
            ...this._def,
            checks: [...this._def.checks, { kind: "trim" }],
        });
    }
    /**
     * @public
     * @return {!ZodString}
     */
    toLowerCase() {
        return new ZodString({
            ...this._def,
            checks: [...this._def.checks, { kind: "toLowerCase" }],
        });
    }
    /**
     * @public
     * @return {!ZodString}
     */
    toUpperCase() {
        return new ZodString({
            ...this._def,
            checks: [...this._def.checks, { kind: "toUpperCase" }],
        });
    }
    /**
     * @public
     * @return {boolean}
     */
    get isDatetime() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "datetime"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isDate() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "date"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isTime() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "time"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isDuration() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "duration"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isEmail() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "email"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isURL() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "url"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isEmoji() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "emoji"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isUUID() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "uuid"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isNANOID() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "nanoid"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isCUID() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "cuid"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isCUID2() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "cuid2"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isULID() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "ulid"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isIP() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "ip"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isCIDR() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "cidr"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isBase64() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "base64"));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isBase64url() {
        // base64url encoding is a modification of base64 that can safely be used in URLs and filenames
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: string, position: (undefined|number), message: (undefined|string)}|{kind: string, value: string, message: (undefined|string)}|{kind: string, regex: !RegExp, message: (undefined|string)}|{kind: string, alg: (undefined|string), message: (undefined|string)}|{kind: string, offset: boolean, local: boolean, precision: (null|number), message: (undefined|string)}|{kind: string, precision: (null|number), message: (undefined|string)}|{kind: string, version: (undefined|string), message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "base64url"));
    }
    /**
     * @public
     * @return {(null|number)}
     */
    get minLength() {
        /** @type {(null|number)} */
        let min = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "min") {
                if (min === null || (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value > min)
                    min = (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return min;
    }
    /**
     * @public
     * @return {(null|number)}
     */
    get maxLength() {
        /** @type {(null|number)} */
        let max = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "max") {
                if (max === null || (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value < max)
                    max = (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return max;
    }
}
exports.ZodString = ZodString;
ZodString.create = (/**
 * @param {(undefined|?)=} params
 * @return {!ZodString}
 */
(params) => {
    return new ZodString({
        checks: [],
        typeName: ZodFirstPartyTypeKind.ZodString,
        coerce: params?.coerce ?? false,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|?)=): !ZodString}
     * @public
     */
    ZodString.create;
}
/** @typedef {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})} */
exports.ZodNumberCheck;
// https://stackoverflow.com/questions/3966484/why-does-modulus-operator-return-fractional-number-in-javascript/31711034#31711034
/**
 * @param {number} val
 * @param {number} step
 * @return {number}
 */
function floatSafeRemainder(val, step) {
    /** @type {number} */
    const valDecCount = (val.toString().split(".")[1] || "").length;
    /** @type {number} */
    const stepDecCount = (step.toString().split(".")[1] || "").length;
    /** @type {number} */
    const decCount = valDecCount > stepDecCount ? valDecCount : stepDecCount;
    /** @type {number} */
    const valInt = Number.parseInt(val.toFixed(decCount).replace(".", ""));
    /** @type {number} */
    const stepInt = Number.parseInt(step.toFixed(decCount).replace(".", ""));
    return (valInt % stepInt) / 10 ** decCount;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodNumberDef() { }
exports.ZodNumberDef = ZodNumberDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!Array<({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})>}
     * @public
     */
    ZodNumberDef.prototype.checks;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNumberDef.prototype.typeName;
    /**
     * @type {boolean}
     * @public
     */
    ZodNumberDef.prototype.coerce;
}
/**
 * @extends {ZodType<number, !ZodNumberDef, number>}
 */
class ZodNumber extends ZodType {
    constructor() {
        super(...arguments);
        this.min = this.gte;
        this.max = this.lte;
        this.step = this.multipleOf;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: number}|{status: string})>|{status: string, value: number}|{status: string})}
     */
    _parse(input) {
        if (this._def.coerce) {
            input.data = Number(input.data);
        }
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.number) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.number,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {(undefined|!tsickle_parseUtil_5.ParseContext)} */
        let ctx = undefined;
        /** @type {!tsickle_parseUtil_5.ParseStatus} */
        const status = new parseUtil_js_1.ParseStatus();
        for (const check of this._def.checks) {
            if (check.kind === "int") {
                if (!util_js_1.util.isInteger(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.invalid_type,
                        expected: "integer",
                        received: "float",
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "min") {
                /** @type {boolean} */
                const tooSmall = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive ? input.data < (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value : input.data <= (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value;
                if (tooSmall) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_small,
                        minimum: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value,
                        type: "number",
                        inclusive: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive,
                        exact: false,
                        message: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "max") {
                /** @type {boolean} */
                const tooBig = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive ? input.data > (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value : input.data >= (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value;
                if (tooBig) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_big,
                        maximum: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).value,
                        type: "number",
                        inclusive: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive,
                        exact: false,
                        message: (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (check)).kind === "multipleOf") {
                if (floatSafeRemainder(input.data, (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value) !== 0) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.not_multiple_of,
                        multipleOf: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                        message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {{kind: string, message: (undefined|string)}} */ (check)).kind === "finite") {
                if (!Number.isFinite(input.data)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.not_finite,
                        message: (/** @type {{kind: string, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else {
                util_js_1.util.assertNever(check);
            }
        }
        return { status: status.value, value: input.data };
    }
    /**
     * @public
     * @param {number} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    gte(value, message) {
        return this.setLimit("min", value, true, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {number} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    gt(value, message) {
        return this.setLimit("min", value, false, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {number} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    lte(value, message) {
        return this.setLimit("max", value, true, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {number} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    lt(value, message) {
        return this.setLimit("max", value, false, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @protected
     * @param {string} kind
     * @param {number} value
     * @param {boolean} inclusive
     * @param {(undefined|string)=} message
     * @return {!ZodNumber}
     */
    setLimit(kind, value, inclusive, message) {
        return new ZodNumber({
            ...this._def,
            checks: [
                ...this._def.checks,
                {
                    kind,
                    value,
                    inclusive,
                    message: errorUtil_js_1.errorUtil.toString(message),
                },
            ],
        });
    }
    /**
     * @public
     * @param {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})} check
     * @return {!ZodNumber}
     */
    _addCheck(check) {
        return new ZodNumber({
            ...this._def,
            checks: [...this._def.checks, check],
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    int(message) {
        return this._addCheck({
            kind: "int",
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    positive(message) {
        return this._addCheck({
            kind: "min",
            value: 0,
            inclusive: false,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    negative(message) {
        return this._addCheck({
            kind: "max",
            value: 0,
            inclusive: false,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    nonpositive(message) {
        return this._addCheck({
            kind: "max",
            value: 0,
            inclusive: true,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    nonnegative(message) {
        return this._addCheck({
            kind: "min",
            value: 0,
            inclusive: true,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {number} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    multipleOf(value, message) {
        return this._addCheck({
            kind: "multipleOf",
            value: value,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    finite(message) {
        return this._addCheck({
            kind: "finite",
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodNumber}
     */
    safe(message) {
        return this._addCheck({
            kind: "min",
            inclusive: true,
            value: Number.MIN_SAFE_INTEGER,
            message: errorUtil_js_1.errorUtil.toString(message),
        })._addCheck({
            kind: "max",
            inclusive: true,
            value: Number.MAX_SAFE_INTEGER,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @return {(null|number)}
     */
    get minValue() {
        /** @type {(null|number)} */
        let min = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "min") {
                if (min === null || (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value > min)
                    min = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return min;
    }
    /**
     * @public
     * @return {(null|number)}
     */
    get maxValue() {
        /** @type {(null|number)} */
        let max = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "max") {
                if (max === null || (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value < max)
                    max = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return max;
    }
    /**
     * @public
     * @return {boolean}
     */
    get isInt() {
        return !!this._def.checks.find((/**
         * @param {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})} ch
         * @return {boolean}
         */
        (ch) => ch.kind === "int" || ((/** @type {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)}|{kind: string, message: (undefined|string)})} */ (ch)).kind === "multipleOf" && util_js_1.util.isInteger((/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value))));
    }
    /**
     * @public
     * @return {boolean}
     */
    get isFinite() {
        /** @type {(null|number)} */
        let max = null;
        /** @type {(null|number)} */
        let min = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "finite" || (/** @type {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})} */ (ch)).kind === "int" || (/** @type {({kind: string, value: number, inclusive: boolean, message: (undefined|string)}|{kind: string, value: number, message: (undefined|string)})} */ (ch)).kind === "multipleOf") {
                return true;
            }
            else if ((/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).kind === "min") {
                if (min === null || (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value > min)
                    min = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
            else if ((/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).kind === "max") {
                if (max === null || (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value < max)
                    max = (/** @type {{kind: string, value: number, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return Number.isFinite(min) && Number.isFinite(max);
    }
}
exports.ZodNumber = ZodNumber;
ZodNumber.create = (/**
 * @param {(undefined|?)=} params
 * @return {!ZodNumber}
 */
(params) => {
    return new ZodNumber({
        checks: [],
        typeName: ZodFirstPartyTypeKind.ZodNumber,
        coerce: params?.coerce || false,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|?)=): !ZodNumber}
     * @public
     */
    ZodNumber.create;
    /**
     * @type {function(number, (undefined|string|?)=): !ZodNumber}
     * @public
     */
    ZodNumber.prototype.min;
    /**
     * @type {function(number, (undefined|string|?)=): !ZodNumber}
     * @public
     */
    ZodNumber.prototype.max;
    /**
     * @type {function(number, (undefined|string|?)=): !ZodNumber}
     * @public
     */
    ZodNumber.prototype.step;
}
/** @typedef {({kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}|{kind: string, value: bigint, message: (undefined|string)})} */
exports.ZodBigIntCheck;
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodBigIntDef() { }
exports.ZodBigIntDef = ZodBigIntDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!Array<({kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}|{kind: string, value: bigint, message: (undefined|string)})>}
     * @public
     */
    ZodBigIntDef.prototype.checks;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodBigIntDef.prototype.typeName;
    /**
     * @type {boolean}
     * @public
     */
    ZodBigIntDef.prototype.coerce;
}
/**
 * @extends {ZodType<bigint, !ZodBigIntDef, bigint>}
 */
class ZodBigInt extends ZodType {
    constructor() {
        super(...arguments);
        this.min = this.gte;
        this.max = this.lte;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: bigint}|{status: string})>|{status: string, value: bigint}|{status: string})}
     */
    _parse(input) {
        if (this._def.coerce) {
            try {
                input.data = BigInt(input.data);
            }
            catch {
                return this._getInvalidInput(input);
            }
        }
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.bigint) {
            return this._getInvalidInput(input);
        }
        /** @type {(undefined|!tsickle_parseUtil_5.ParseContext)} */
        let ctx = undefined;
        /** @type {!tsickle_parseUtil_5.ParseStatus} */
        const status = new parseUtil_js_1.ParseStatus();
        for (const check of this._def.checks) {
            if (check.kind === "min") {
                /** @type {boolean} */
                const tooSmall = (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive ? input.data < (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value : input.data <= (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value;
                if (tooSmall) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_small,
                        type: "bigint",
                        minimum: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value,
                        inclusive: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive,
                        message: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {({kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}|{kind: string, value: bigint, message: (undefined|string)})} */ (check)).kind === "max") {
                /** @type {boolean} */
                const tooBig = (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive ? input.data > (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value : input.data >= (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value;
                if (tooBig) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_big,
                        type: "bigint",
                        maximum: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).value,
                        inclusive: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).inclusive,
                        message: (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {{kind: string, value: bigint, message: (undefined|string)}} */ (check)).kind === "multipleOf") {
                if (input.data % (/** @type {{kind: string, value: bigint, message: (undefined|string)}} */ (check)).value !== BigInt(0)) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.not_multiple_of,
                        multipleOf: (/** @type {{kind: string, value: bigint, message: (undefined|string)}} */ (check)).value,
                        message: (/** @type {{kind: string, value: bigint, message: (undefined|string)}} */ (check)).message,
                    });
                    status.dirty();
                }
            }
            else {
                util_js_1.util.assertNever(check);
            }
        }
        return { status: status.value, value: input.data };
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {{status: string}}
     */
    _getInvalidInput(input) {
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = this._getOrReturnCtx(input);
        (0, parseUtil_js_1.addIssueToContext)(ctx, {
            code: ZodError_js_1.ZodIssueCode.invalid_type,
            expected: util_js_1.ZodParsedType.bigint,
            received: ctx.parsedType,
        });
        return parseUtil_js_1.INVALID;
    }
    /**
     * @public
     * @param {bigint} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    gte(value, message) {
        return this.setLimit("min", value, true, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {bigint} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    gt(value, message) {
        return this.setLimit("min", value, false, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {bigint} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    lte(value, message) {
        return this.setLimit("max", value, true, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @public
     * @param {bigint} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    lt(value, message) {
        return this.setLimit("max", value, false, errorUtil_js_1.errorUtil.toString(message));
    }
    /**
     * @protected
     * @param {string} kind
     * @param {bigint} value
     * @param {boolean} inclusive
     * @param {(undefined|string)=} message
     * @return {!ZodBigInt}
     */
    setLimit(kind, value, inclusive, message) {
        return new ZodBigInt({
            ...this._def,
            checks: [
                ...this._def.checks,
                {
                    kind,
                    value,
                    inclusive,
                    message: errorUtil_js_1.errorUtil.toString(message),
                },
            ],
        });
    }
    /**
     * @public
     * @param {({kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}|{kind: string, value: bigint, message: (undefined|string)})} check
     * @return {!ZodBigInt}
     */
    _addCheck(check) {
        return new ZodBigInt({
            ...this._def,
            checks: [...this._def.checks, check],
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    positive(message) {
        return this._addCheck({
            kind: "min",
            value: BigInt(0),
            inclusive: false,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    negative(message) {
        return this._addCheck({
            kind: "max",
            value: BigInt(0),
            inclusive: false,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    nonpositive(message) {
        return this._addCheck({
            kind: "max",
            value: BigInt(0),
            inclusive: true,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    nonnegative(message) {
        return this._addCheck({
            kind: "min",
            value: BigInt(0),
            inclusive: true,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {bigint} value
     * @param {(undefined|string|?)=} message
     * @return {!ZodBigInt}
     */
    multipleOf(value, message) {
        return this._addCheck({
            kind: "multipleOf",
            value,
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @return {(null|bigint)}
     */
    get minValue() {
        /** @type {(null|bigint)} */
        let min = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "min") {
                if (min === null || (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (ch)).value > min)
                    min = (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return min;
    }
    /**
     * @public
     * @return {(null|bigint)}
     */
    get maxValue() {
        /** @type {(null|bigint)} */
        let max = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "max") {
                if (max === null || (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (ch)).value < max)
                    max = (/** @type {{kind: string, value: bigint, inclusive: boolean, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return max;
    }
}
exports.ZodBigInt = ZodBigInt;
ZodBigInt.create = (/**
 * @param {(undefined|?)=} params
 * @return {!ZodBigInt}
 */
(params) => {
    return new ZodBigInt({
        checks: [],
        typeName: ZodFirstPartyTypeKind.ZodBigInt,
        coerce: params?.coerce ?? false,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|?)=): !ZodBigInt}
     * @public
     */
    ZodBigInt.create;
    /**
     * @type {function(bigint, (undefined|string|?)=): !ZodBigInt}
     * @public
     */
    ZodBigInt.prototype.min;
    /**
     * @type {function(bigint, (undefined|string|?)=): !ZodBigInt}
     * @public
     */
    ZodBigInt.prototype.max;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodBooleanDef() { }
exports.ZodBooleanDef = ZodBooleanDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodBooleanDef.prototype.typeName;
    /**
     * @type {boolean}
     * @public
     */
    ZodBooleanDef.prototype.coerce;
}
/**
 * @extends {ZodType<boolean, !ZodBooleanDef, boolean>}
 */
class ZodBoolean extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: boolean}|{status: string})>|{status: string, value: boolean}|{status: string})}
     */
    _parse(input) {
        if (this._def.coerce) {
            input.data = Boolean(input.data);
        }
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.boolean) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.boolean,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodBoolean = ZodBoolean;
ZodBoolean.create = (/**
 * @param {(undefined|?)=} params
 * @return {!ZodBoolean}
 */
(params) => {
    return new ZodBoolean({
        typeName: ZodFirstPartyTypeKind.ZodBoolean,
        coerce: params?.coerce || false,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|?)=): !ZodBoolean}
     * @public
     */
    ZodBoolean.create;
}
/** @typedef {{kind: string, value: number, message: (undefined|string)}} */
exports.ZodDateCheck;
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodDateDef() { }
exports.ZodDateDef = ZodDateDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!Array<{kind: string, value: number, message: (undefined|string)}>}
     * @public
     */
    ZodDateDef.prototype.checks;
    /**
     * @type {boolean}
     * @public
     */
    ZodDateDef.prototype.coerce;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodDateDef.prototype.typeName;
}
/**
 * @extends {ZodType<!Date, !ZodDateDef, !Date>}
 */
class ZodDate extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        if (this._def.coerce) {
            input.data = new Date(input.data);
        }
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.date) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.date,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        if (Number.isNaN(input.data.getTime())) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_date,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {!tsickle_parseUtil_5.ParseStatus} */
        const status = new parseUtil_js_1.ParseStatus();
        /** @type {(undefined|!tsickle_parseUtil_5.ParseContext)} */
        let ctx = undefined;
        for (const check of this._def.checks) {
            if (check.kind === "min") {
                if (input.data.getTime() < (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_small,
                        message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                        inclusive: true,
                        exact: false,
                        minimum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                        type: "date",
                    });
                    status.dirty();
                }
            }
            else if ((/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).kind === "max") {
                if (input.data.getTime() > (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value) {
                    ctx = this._getOrReturnCtx(input, ctx);
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.too_big,
                        message: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).message,
                        inclusive: true,
                        exact: false,
                        maximum: (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (check)).value,
                        type: "date",
                    });
                    status.dirty();
                }
            }
            else {
                util_js_1.util.assertNever(check);
            }
        }
        return {
            status: status.value,
            value: new Date(((/** @type {!Date} */ (input.data))).getTime()),
        };
    }
    /**
     * @public
     * @param {{kind: string, value: number, message: (undefined|string)}} check
     * @return {!ZodDate}
     */
    _addCheck(check) {
        return new ZodDate({
            ...this._def,
            checks: [...this._def.checks, check],
        });
    }
    /**
     * @public
     * @param {!Date} minDate
     * @param {(undefined|string|?)=} message
     * @return {!ZodDate}
     */
    min(minDate, message) {
        return this._addCheck({
            kind: "min",
            value: minDate.getTime(),
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @param {!Date} maxDate
     * @param {(undefined|string|?)=} message
     * @return {!ZodDate}
     */
    max(maxDate, message) {
        return this._addCheck({
            kind: "max",
            value: maxDate.getTime(),
            message: errorUtil_js_1.errorUtil.toString(message),
        });
    }
    /**
     * @public
     * @return {(null|!Date)}
     */
    get minDate() {
        /** @type {(null|number)} */
        let min = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "min") {
                if (min === null || (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value > min)
                    min = (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return min != null ? new Date(min) : null;
    }
    /**
     * @public
     * @return {(null|!Date)}
     */
    get maxDate() {
        /** @type {(null|number)} */
        let max = null;
        for (const ch of this._def.checks) {
            if (ch.kind === "max") {
                if (max === null || (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value < max)
                    max = (/** @type {{kind: string, value: number, message: (undefined|string)}} */ (ch)).value;
            }
        }
        return max != null ? new Date(max) : null;
    }
}
exports.ZodDate = ZodDate;
ZodDate.create = (/**
 * @param {(undefined|?)=} params
 * @return {!ZodDate}
 */
(params) => {
    return new ZodDate({
        checks: [],
        coerce: params?.coerce || false,
        typeName: ZodFirstPartyTypeKind.ZodDate,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|?)=): !ZodDate}
     * @public
     */
    ZodDate.create;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodSymbolDef() { }
exports.ZodSymbolDef = ZodSymbolDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodSymbolDef.prototype.typeName;
}
/**
 * @extends {ZodType<symbol, !ZodSymbolDef, symbol>}
 */
class ZodSymbol extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.symbol) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.symbol,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodSymbol = ZodSymbol;
ZodSymbol.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodSymbol}
 */
(params) => {
    return new ZodSymbol({
        typeName: ZodFirstPartyTypeKind.ZodSymbol,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodSymbol}
     * @public
     */
    ZodSymbol.create;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodUndefinedDef() { }
exports.ZodUndefinedDef = ZodUndefinedDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodUndefinedDef.prototype.typeName;
}
/**
 * @extends {ZodType<undefined, !ZodUndefinedDef, undefined>}
 */
class ZodUndefined extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.undefined) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.undefined,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodUndefined = ZodUndefined;
ZodUndefined.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodUndefined}
 */
(params) => {
    return new ZodUndefined({
        typeName: ZodFirstPartyTypeKind.ZodUndefined,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUndefined}
     * @public
     */
    ZodUndefined.create;
    /**
     * @type {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})}
     * @public
     */
    ZodUndefined.prototype.params;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodNullDef() { }
exports.ZodNullDef = ZodNullDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNullDef.prototype.typeName;
}
/**
 * @extends {ZodType<null, !ZodNullDef, null>}
 */
class ZodNull extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.null) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.null,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodNull = ZodNull;
ZodNull.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodNull}
 */
(params) => {
    return new ZodNull({
        typeName: ZodFirstPartyTypeKind.ZodNull,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNull}
     * @public
     */
    ZodNull.create;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodAnyDef() { }
exports.ZodAnyDef = ZodAnyDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodAnyDef.prototype.typeName;
}
/**
 * @extends {ZodType<?, !ZodAnyDef, ?>}
 */
class ZodAny extends ZodType {
    constructor() {
        super(...arguments);
        // to prevent instances of other classes from extending ZodAny. this causes issues with catchall in ZodObject.
        this._any = (/** @type {boolean} */ (true));
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodAny = ZodAny;
ZodAny.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodAny}
 */
(params) => {
    return new ZodAny({
        typeName: ZodFirstPartyTypeKind.ZodAny,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodAny}
     * @public
     */
    ZodAny.create;
    /**
     * @type {boolean}
     * @public
     */
    ZodAny.prototype._any;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodUnknownDef() { }
exports.ZodUnknownDef = ZodUnknownDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodUnknownDef.prototype.typeName;
}
/**
 * @extends {ZodType<*, !ZodUnknownDef, *>}
 */
class ZodUnknown extends ZodType {
    constructor() {
        super(...arguments);
        // required
        this._unknown = (/** @type {boolean} */ (true));
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodUnknown = ZodUnknown;
ZodUnknown.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodUnknown}
 */
(params) => {
    return new ZodUnknown({
        typeName: ZodFirstPartyTypeKind.ZodUnknown,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUnknown}
     * @public
     */
    ZodUnknown.create;
    /**
     * @type {boolean}
     * @public
     */
    ZodUnknown.prototype._unknown;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodNeverDef() { }
exports.ZodNeverDef = ZodNeverDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNeverDef.prototype.typeName;
}
/**
 * @extends {ZodType<?, !ZodNeverDef, ?>}
 */
class ZodNever extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = this._getOrReturnCtx(input);
        (0, parseUtil_js_1.addIssueToContext)(ctx, {
            code: ZodError_js_1.ZodIssueCode.invalid_type,
            expected: util_js_1.ZodParsedType.never,
            received: ctx.parsedType,
        });
        return parseUtil_js_1.INVALID;
    }
}
exports.ZodNever = ZodNever;
ZodNever.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodNever}
 */
(params) => {
    return new ZodNever({
        typeName: ZodFirstPartyTypeKind.ZodNever,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNever}
     * @public
     */
    ZodNever.create;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodVoidDef() { }
exports.ZodVoidDef = ZodVoidDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodVoidDef.prototype.typeName;
}
/**
 * @extends {ZodType<void, !ZodVoidDef, void>}
 */
class ZodVoid extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.undefined) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.void,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
}
exports.ZodVoid = ZodVoid;
ZodVoid.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodVoid}
 */
(params) => {
    return new ZodVoid({
        typeName: ZodFirstPartyTypeKind.ZodVoid,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodVoid}
     * @public
     */
    ZodVoid.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodArrayDef() { }
exports.ZodArrayDef = ZodArrayDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodArrayDef.prototype.type;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodArrayDef.prototype.typeName;
    /**
     * @type {(null|{value: number, message: (undefined|string)})}
     * @public
     */
    ZodArrayDef.prototype.exactLength;
    /**
     * @type {(null|{value: number, message: (undefined|string)})}
     * @public
     */
    ZodArrayDef.prototype.minLength;
    /**
     * @type {(null|{value: number, message: (undefined|string)})}
     * @public
     */
    ZodArrayDef.prototype.maxLength;
}
/** @typedef {string} */
exports.ArrayCardinality;
/** @typedef {?} */
exports.arrayOutputType;
/**
 * @template T, Cardinality
 * @extends {ZodType<?, !ZodArrayDef, ?>}
 */
class ZodArray extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx, status } = this._processInputParams(input);
        /** @type {!ZodArrayDef<T>} */
        const def = this._def;
        if (ctx.parsedType !== util_js_1.ZodParsedType.array) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.array,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        if (def.exactLength !== null) {
            /** @type {boolean} */
            const tooBig = ctx.data.length > def.exactLength.value;
            /** @type {boolean} */
            const tooSmall = ctx.data.length < def.exactLength.value;
            if (tooBig || tooSmall) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: tooBig ? ZodError_js_1.ZodIssueCode.too_big : ZodError_js_1.ZodIssueCode.too_small,
                    minimum: (/** @type {number} */ ((tooSmall ? def.exactLength.value : undefined))),
                    maximum: (/** @type {number} */ ((tooBig ? def.exactLength.value : undefined))),
                    type: "array",
                    inclusive: true,
                    exact: true,
                    message: def.exactLength.message,
                });
                status.dirty();
            }
        }
        if (def.minLength !== null) {
            if (ctx.data.length < def.minLength.value) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: ZodError_js_1.ZodIssueCode.too_small,
                    minimum: def.minLength.value,
                    type: "array",
                    inclusive: true,
                    exact: false,
                    message: def.minLength.message,
                });
                status.dirty();
            }
        }
        if (def.maxLength !== null) {
            if (ctx.data.length > def.maxLength.value) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: ZodError_js_1.ZodIssueCode.too_big,
                    maximum: def.maxLength.value,
                    type: "array",
                    inclusive: true,
                    exact: false,
                    message: def.maxLength.message,
                });
                status.dirty();
            }
        }
        if (ctx.common.async) {
            return Promise.all(((/** @type {!Array<?>} */ ([...ctx.data]))).map((/**
             * @param {?} item
             * @param {number} i
             * @return {!Promise<({status: string, value: ?}|{status: string})>}
             */
            (item, i) => {
                return def.type._parseAsync(new ParseInputLazyPath(ctx, item, ctx.path, i));
            }))).then((/**
             * @param {!Array<({status: string, value: ?}|{status: string})>} result
             * @return {({status: string, value: ?}|{status: string})}
             */
            (result) => {
                return parseUtil_js_1.ParseStatus.mergeArray(status, result);
            }));
        }
        /** @type {!Array<({status: string, value: ?}|{status: string})>} */
        const result = ((/** @type {!Array<?>} */ ([...ctx.data]))).map((/**
         * @param {?} item
         * @param {number} i
         * @return {({status: string, value: ?}|{status: string})}
         */
        (item, i) => {
            return def.type._parseSync(new ParseInputLazyPath(ctx, item, ctx.path, i));
        }));
        return parseUtil_js_1.ParseStatus.mergeArray(status, result);
    }
    /**
     * @public
     * @return {T}
     */
    get element() {
        return this._def.type;
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} minLength
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    min(minLength, message) {
        return (/** @type {?} */ (new ZodArray({
            ...(/** @type {!ZodArray} */ (this))._def,
            minLength: { value: minLength, message: errorUtil_js_1.errorUtil.toString(message) },
        })));
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} maxLength
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    max(maxLength, message) {
        return (/** @type {?} */ (new ZodArray({
            ...(/** @type {!ZodArray} */ (this))._def,
            maxLength: { value: maxLength, message: errorUtil_js_1.errorUtil.toString(message) },
        })));
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} len
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    length(len, message) {
        return (/** @type {?} */ (new ZodArray({
            ...(/** @type {!ZodArray} */ (this))._def,
            exactLength: { value: len, message: errorUtil_js_1.errorUtil.toString(message) },
        })));
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodArray<T, string>}
     */
    nonempty(message) {
        return (/** @type {?} */ (this.min(1, message)));
    }
}
exports.ZodArray = ZodArray;
ZodArray.create = (/**
 * @template El
 * @param {?} schema
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodArray<?, string>}
 */
(schema, params) => {
    return new ZodArray({
        type: schema,
        minLength: null,
        maxLength: null,
        exactLength: null,
        typeName: ZodFirstPartyTypeKind.ZodArray,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodArray<?, string>}
     * @public
     */
    ZodArray.create;
}
/** @typedef {!ZodArray<?, string>} */
exports.ZodNonEmptyArray;
/** @typedef {string} */
exports.UnknownKeysParam;
/**
 * @record
 * @template T, UnknownKeys, Catchall
 * @extends {ZodTypeDef}
 */
function ZodObjectDef() { }
exports.ZodObjectDef = ZodObjectDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodObjectDef.prototype.typeName;
    /**
     * @type {function(): T}
     * @public
     */
    ZodObjectDef.prototype.shape;
    /**
     * @type {Catchall}
     * @public
     */
    ZodObjectDef.prototype.catchall;
    /**
     * @type {UnknownKeys}
     * @public
     */
    ZodObjectDef.prototype.unknownKeys;
}
/** @typedef {?} */
exports.mergeTypes;
/** @typedef {?} */
exports.objectOutputType;
/** @typedef {?} */
exports.baseObjectOutputType;
/** @typedef {?} */
exports.objectInputType;
/** @typedef {?} */
exports.baseObjectInputType;
/** @typedef {?} */
exports.CatchallOutput;
/** @typedef {?} */
exports.CatchallInput;
/** @typedef {?} */
exports.PassthroughType;
/** @typedef {?} */
exports.deoptional;
/** @typedef {!ZodObject<!Object<string,!ZodType<?, ?, ?>>, string, !ZodType<?, ?, ?>, ?, ?>} */
exports.SomeZodObject;
/** @typedef {?} */
exports.noUnrecognized;
/**
 * @param {!ZodType<?, ?, ?>} schema
 * @return {?}
 */
function deepPartialify(schema) {
    if (schema instanceof ZodObject) {
        /** @type {?} */
        const newShape = {};
        for (const key in (/** @type {!ZodObject<?, ?, ?, ?, ?>} */ (schema)).shape) {
            /** @type {?} */
            const fieldSchema = (/** @type {!ZodObject<?, ?, ?, ?, ?>} */ (schema)).shape[key];
            newShape[key] = ZodOptional.create(deepPartialify(fieldSchema));
        }
        return (/** @type {?} */ (new ZodObject({
            ...(/** @type {!ZodObject<?, ?, ?, ?, ?>} */ (schema))._def,
            shape: (/**
             * @return {?}
             */
            () => newShape),
        })));
    }
    else if (schema instanceof ZodArray) {
        return new ZodArray({
            ...(/** @type {!ZodArray<?, ?>} */ (schema))._def,
            type: deepPartialify((/** @type {!ZodArray<?, ?>} */ (schema)).element),
        });
    }
    else if (schema instanceof ZodOptional) {
        return ZodOptional.create(deepPartialify((/** @type {!ZodOptional<?>} */ (schema)).unwrap()));
    }
    else if (schema instanceof ZodNullable) {
        return ZodNullable.create(deepPartialify((/** @type {!ZodNullable<?>} */ (schema)).unwrap()));
    }
    else if (schema instanceof ZodTuple) {
        return ZodTuple.create((/** @type {!ZodTuple<?, ?>} */ (schema)).items.map((/**
         * @param {?} item
         * @return {?}
         */
        (item) => deepPartialify(item))));
    }
    else {
        return schema;
    }
}
/**
 * @template T, UnknownKeys, Catchall, Output, Input
 * @extends {ZodType<Output, !ZodObjectDef<T, UnknownKeys>, Input>}
 */
class ZodObject extends ZodType {
    constructor() {
        super(...arguments);
        this._cached = null;
        /**
         * @deprecated In most cases, this is no longer needed - unknown properties are now silently stripped.
         * If you want to pass through unknown properties, use `.passthrough()` instead.
         */
        this.nonstrict = this.passthrough;
        // extend<
        //   Augmentation extends ZodRawShape,
        //   NewOutput extends util.flatten<{
        //     [k in keyof Augmentation | keyof Output]: k extends keyof Augmentation
        //       ? Augmentation[k]["_output"]
        //       : k extends keyof Output
        //       ? Output[k]
        //       : never;
        //   }>,
        //   NewInput extends util.flatten<{
        //     [k in keyof Augmentation | keyof Input]: k extends keyof Augmentation
        //       ? Augmentation[k]["_input"]
        //       : k extends keyof Input
        //       ? Input[k]
        //       : never;
        //   }>
        // >(
        //   augmentation: Augmentation
        // ): ZodObject<
        //   extendShape<T, Augmentation>,
        //   UnknownKeys,
        //   Catchall,
        //   NewOutput,
        //   NewInput
        // > {
        //   return new ZodObject({
        //     ...this._def,
        //     shape: () => ({
        //       ...this._def.shape(),
        //       ...augmentation,
        //     }),
        //   }) as any;
        // }
        /**
         * @deprecated Use `.extend` instead
         *
         */
        this.augment = this.extend;
    }
    /**
     * @public
     * @return {{shape: T, keys: !Array<string>}}
     */
    _getCached() {
        if (this._cached !== null)
            return this._cached;
        /** @type {T} */
        const shape = this._def.shape();
        /** @type {!Array<string>} */
        const keys = util_js_1.util.objectKeys(shape);
        this._cached = { shape, keys };
        return this._cached;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.object) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.object,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        const { status, ctx } = this._processInputParams(input);
        const { shape, keys: shapeKeys } = this._getCached();
        /** @type {!Array<string>} */
        const extraKeys = [];
        if (!(this._def.catchall instanceof ZodNever && this._def.unknownKeys === "strip")) {
            for (const key in ctx.data) {
                if (!shapeKeys.includes(key)) {
                    extraKeys.push(key);
                }
            }
        }
        /** @type {!Array<{key: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), value: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), alwaysSet: (undefined|boolean)}>} */
        const pairs = [];
        for (const key of shapeKeys) {
            /** @type {!ZodType<?, ?, ?>} */
            const keyValidator = (/** @type {!ZodType<?, ?, ?>} */ (shape[key]));
            /** @type {?} */
            const value = ctx.data[key];
            pairs.push({
                key: { status: "valid", value: key },
                value: keyValidator._parse(new ParseInputLazyPath(ctx, value, ctx.path, key)),
                alwaysSet: key in ctx.data,
            });
        }
        if (this._def.catchall instanceof ZodNever) {
            /** @type {UnknownKeys} */
            const unknownKeys = this._def.unknownKeys;
            if (unknownKeys === "passthrough") {
                for (const key of extraKeys) {
                    pairs.push({
                        key: { status: "valid", value: key },
                        value: { status: "valid", value: ctx.data[key] },
                    });
                }
            }
            else if (unknownKeys === "strict") {
                if (extraKeys.length > 0) {
                    (0, parseUtil_js_1.addIssueToContext)(ctx, {
                        code: ZodError_js_1.ZodIssueCode.unrecognized_keys,
                        keys: extraKeys,
                    });
                    status.dirty();
                }
            }
            else if (unknownKeys === "strip") {
            }
            else {
                throw new Error(`Internal ZodObject error: invalid unknownKeys value.`);
            }
        }
        else {
            // run catchall validation
            /** @type {Catchall} */
            const catchall = this._def.catchall;
            for (const key of extraKeys) {
                /** @type {?} */
                const value = ctx.data[key];
                pairs.push({
                    key: { status: "valid", value: key },
                    value: catchall._parse(new ParseInputLazyPath(ctx, value, ctx.path, key) //, ctx.child(key), value, getParsedType(value)
                    ),
                    alwaysSet: key in ctx.data,
                });
            }
        }
        if (ctx.common.async) {
            return Promise.resolve()
                .then((/**
             * @return {!Promise<!Array<?>>}
             */
            async () => {
                /** @type {!Array<?>} */
                const syncPairs = [];
                for (const pair of pairs) {
                    /** @type {({status: string, value: ?}|{status: string})} */
                    const key = await pair.key;
                    /** @type {({status: string, value: ?}|{status: string})} */
                    const value = await pair.value;
                    syncPairs.push({
                        key,
                        value,
                        alwaysSet: pair.alwaysSet,
                    });
                }
                return syncPairs;
            }))
                .then((/**
             * @param {!Array<?>} syncPairs
             * @return {({status: string, value: ?}|{status: string})}
             */
            (syncPairs) => {
                return parseUtil_js_1.ParseStatus.mergeObjectSync(status, syncPairs);
            }));
        }
        else {
            return parseUtil_js_1.ParseStatus.mergeObjectSync(status, (/** @type {?} */ (pairs)));
        }
    }
    /**
     * @public
     * @return {T}
     */
    get shape() {
        return this._def.shape();
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodObject<T, string, Catchall, ?, ?>}
     */
    strict(message) {
        errorUtil_js_1.errorUtil.errToObj;
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            unknownKeys: "strict",
            ...(message !== undefined
                ? {
                    errorMap: (/**
                     * @param {(!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue)} issue
                     * @param {{defaultError: string, data: ?}} ctx
                     * @return {{message: string}}
                     */
                    (issue, ctx) => {
                        /** @type {string} */
                        const defaultError = this._def.errorMap?.(issue, ctx).message ?? ctx.defaultError;
                        if (issue.code === "unrecognized_keys")
                            return {
                                message: errorUtil_js_1.errorUtil.errToObj(message).message ?? defaultError,
                            };
                        return {
                            message: defaultError,
                        };
                    }),
                }
                : {}),
        })));
    }
    /**
     * @public
     * @return {!ZodObject<T, string, Catchall, ?, ?>}
     */
    strip() {
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            unknownKeys: "strip",
        })));
    }
    /**
     * @public
     * @return {!ZodObject<T, string, Catchall, ?, ?>}
     */
    passthrough() {
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            unknownKeys: "passthrough",
        })));
    }
    // const AugmentFactory =
    //   <Def extends ZodObjectDef>(def: Def) =>
    //   <Augmentation extends ZodRawShape>(
    //     augmentation: Augmentation
    //   ): ZodObject<
    //     extendShape<ReturnType<Def["shape"]>, Augmentation>,
    //     Def["unknownKeys"],
    //     Def["catchall"]
    //   > => {
    //     return new ZodObject({
    //       ...def,
    //       shape: () => ({
    //         ...def.shape(),
    //         ...augmentation,
    //       }),
    //     }) as any;
    //   };
    /**
     * @public
     * @template Augmentation
     * @param {?} augmentation
     * @return {!ZodObject<?, UnknownKeys, Catchall, ?, ?>}
     */
    extend(augmentation) {
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            shape: (/**
             * @return {?}
             */
            () => ({
                ...this._def.shape(),
                ...augmentation,
            })),
        })));
    }
    /**
     * Prior to zod\@1.0.12 there was a bug in the
     * inferred type of merged objects. Please
     * upgrade if you are experiencing issues.
     * @public
     * @template Incoming, Augmentation
     * @param {Incoming} merging
     * @return {!ZodObject<?, ?, ?, ?, ?>}
     */
    merge(merging) {
        /** @type {?} */
        const merged = (/** @type {?} */ (new ZodObject({
            unknownKeys: merging._def.unknownKeys,
            catchall: merging._def.catchall,
            shape: (/**
             * @return {?}
             */
            () => ({
                ...this._def.shape(),
                ...merging._def.shape(),
            })),
            typeName: ZodFirstPartyTypeKind.ZodObject,
        })));
        return merged;
    }
    // merge<
    //   Incoming extends AnyZodObject,
    //   Augmentation extends Incoming["shape"],
    //   NewOutput extends {
    //     [k in keyof Augmentation | keyof Output]: k extends keyof Augmentation
    //       ? Augmentation[k]["_output"]
    //       : k extends keyof Output
    //       ? Output[k]
    //       : never;
    //   },
    //   NewInput extends {
    //     [k in keyof Augmentation | keyof Input]: k extends keyof Augmentation
    //       ? Augmentation[k]["_input"]
    //       : k extends keyof Input
    //       ? Input[k]
    //       : never;
    //   }
    // >(
    //   merging: Incoming
    // ): ZodObject<
    //   extendShape<T, ReturnType<Incoming["_def"]["shape"]>>,
    //   Incoming["_def"]["unknownKeys"],
    //   Incoming["_def"]["catchall"],
    //   NewOutput,
    //   NewInput
    // > {
    //   const merged: any = new ZodObject({
    //     unknownKeys: merging._def.unknownKeys,
    //     catchall: merging._def.catchall,
    //     shape: () =>
    //       objectUtil.mergeShapes(this._def.shape(), merging._def.shape()),
    //     typeName: ZodFirstPartyTypeKind.ZodObject,
    //   }) as any;
    //   return merged;
    // }
    /**
     * @public
     * @template Key, Schema
     * @param {Key} key
     * @param {Schema} schema
     * @return {!ZodObject<?, UnknownKeys, Catchall, ?, ?>}
     */
    setKey(key, schema) {
        return (/** @type {?} */ (this.augment({ [key]: schema })));
    }
    // merge<Incoming extends AnyZodObject>(
    //   merging: Incoming
    // ): //ZodObject<T & Incoming["_shape"], UnknownKeys, Catchall> = (merging) => {
    // ZodObject<
    //   extendShape<T, ReturnType<Incoming["_def"]["shape"]>>,
    //   Incoming["_def"]["unknownKeys"],
    //   Incoming["_def"]["catchall"]
    // > {
    //   // const mergedShape = objectUtil.mergeShapes(
    //   //   this._def.shape(),
    //   //   merging._def.shape()
    //   // );
    //   const merged: any = new ZodObject({
    //     unknownKeys: merging._def.unknownKeys,
    //     catchall: merging._def.catchall,
    //     shape: () =>
    //       objectUtil.mergeShapes(this._def.shape(), merging._def.shape()),
    //     typeName: ZodFirstPartyTypeKind.ZodObject,
    //   }) as any;
    //   return merged;
    // }
    /**
     * @public
     * @template Index
     * @param {Index} index
     * @return {!ZodObject<T, UnknownKeys, Index, ?, ?>}
     */
    catchall(index) {
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            catchall: index,
        })));
    }
    /**
     * @public
     * @template Mask
     * @param {Mask} mask
     * @return {!ZodObject<?, UnknownKeys, Catchall, ?, ?>}
     */
    pick(mask) {
        /** @type {?} */
        const shape = {};
        for (const key of util_js_1.util.objectKeys(mask)) {
            if (mask[key] && this.shape[key]) {
                shape[key] = this.shape[key];
            }
        }
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            shape: (/**
             * @return {?}
             */
            () => shape),
        })));
    }
    /**
     * @public
     * @template Mask
     * @param {Mask} mask
     * @return {!ZodObject<?, UnknownKeys, Catchall, ?, ?>}
     */
    omit(mask) {
        /** @type {?} */
        const shape = {};
        for (const key of util_js_1.util.objectKeys(this.shape)) {
            if (!mask[key]) {
                shape[key] = this.shape[key];
            }
        }
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            shape: (/**
             * @return {?}
             */
            () => shape),
        })));
    }
    /**
     * @deprecated
     * @public
     * @return {?}
     */
    deepPartial() {
        return deepPartialify(this);
    }
    /**
     * @public
     * @param {?=} mask
     * @return {?}
     */
    partial(mask) {
        /** @type {?} */
        const newShape = {};
        for (const key of util_js_1.util.objectKeys(this.shape)) {
            /** @type {!ZodType<?, ?, ?>} */
            const fieldSchema = (/** @type {!ZodType<?, ?, ?>} */ (this.shape[key]));
            if (mask && !mask[key]) {
                newShape[key] = fieldSchema;
            }
            else {
                newShape[key] = fieldSchema.optional();
            }
        }
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            shape: (/**
             * @return {?}
             */
            () => newShape),
        })));
    }
    /**
     * @public
     * @param {?=} mask
     * @return {?}
     */
    required(mask) {
        /** @type {?} */
        const newShape = {};
        for (const key of util_js_1.util.objectKeys(this.shape)) {
            if (mask && !mask[key]) {
                newShape[key] = this.shape[key];
            }
            else {
                /** @type {!ZodType<?, ?, ?>} */
                const fieldSchema = this.shape[key];
                /** @type {!ZodType<?, ?, ?>} */
                let newField = fieldSchema;
                while (newField instanceof ZodOptional) {
                    newField = ((/** @type {!ZodOptional<?>} */ (newField)))._def.innerType;
                }
                newShape[key] = newField;
            }
        }
        return (/** @type {?} */ (new ZodObject({
            ...this._def,
            shape: (/**
             * @return {?}
             */
            () => newShape),
        })));
    }
    /**
     * @public
     * @return {!ZodEnum<?>}
     */
    keyof() {
        return (/** @type {?} */ (createZodEnum((/** @type {!Array<?>} */ (util_js_1.util.objectKeys(this.shape))))));
    }
}
exports.ZodObject = ZodObject;
ZodObject.create = (/**
 * @template Shape
 * @param {?} shape
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
 */
(shape, params) => {
    return (/** @type {?} */ (new ZodObject({
        shape: (/**
         * @return {?}
         */
        () => shape),
        unknownKeys: "strip",
        catchall: ZodNever.create(),
        typeName: ZodFirstPartyTypeKind.ZodObject,
        ...processCreateParams(params),
    })));
});
ZodObject.strictCreate = (/**
 * @template Shape
 * @param {?} shape
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
 */
(shape, params) => {
    return (/** @type {?} */ (new ZodObject({
        shape: (/**
         * @return {?}
         */
        () => shape),
        unknownKeys: "strict",
        catchall: ZodNever.create(),
        typeName: ZodFirstPartyTypeKind.ZodObject,
        ...processCreateParams(params),
    })));
});
ZodObject.lazycreate = (/**
 * @template Shape
 * @param {function(): ?} shape
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
 */
(shape, params) => {
    return (/** @type {?} */ (new ZodObject({
        shape,
        unknownKeys: "strip",
        catchall: ZodNever.create(),
        typeName: ZodFirstPartyTypeKind.ZodObject,
        ...processCreateParams(params),
    })));
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
     * @public
     */
    ZodObject.create;
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
     * @public
     */
    ZodObject.strictCreate;
    /**
     * @type {function(function(): ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}
     * @public
     */
    ZodObject.lazycreate;
    /**
     * @type {(null|{shape: T, keys: !Array<string>})}
     * @private
     */
    ZodObject.prototype._cached;
    /**
     * @deprecated In most cases, this is no longer needed - unknown properties are now silently stripped.
     * If you want to pass through unknown properties, use `.passthrough()` instead.
     * @type {function(): !ZodObject<T, string, Catchall, ?, ?>}
     * @public
     */
    ZodObject.prototype.nonstrict;
    /**
     * @deprecated Use `.extend` instead
     *
     * @type {function(?): !ZodObject<?, UnknownKeys, Catchall, ?, ?>}
     * @public
     */
    ZodObject.prototype.augment;
}
/** @typedef {!ZodObject<?, ?, ?, ?, ?>} */
exports.AnyZodObject;
/** @typedef {!Array<?>} */
exports.ZodUnionOptions;
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodUnionDef() { }
exports.ZodUnionDef = ZodUnionDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodUnionDef.prototype.options;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodUnionDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<?, !ZodUnionDef, ?>}
 */
class ZodUnion extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        /** @type {T} */
        const options = this._def.options;
        /**
         * @param {!Array<{ctx: !tsickle_parseUtil_5.ParseContext, result: ({status: string, value: ?}|{status: string})}>} results
         * @return {({status: string, value: ?}|{status: string})}
         */
        function handleResults(results) {
            // return first issue-free validation if it exists
            for (const result of results) {
                if (result.result.status === "valid") {
                    return result.result;
                }
            }
            for (const result of results) {
                if (result.result.status === "dirty") {
                    // add issues from dirty option
                    ctx.common.issues.push(...result.ctx.common.issues);
                    return result.result;
                }
            }
            // return invalid
            /** @type {!Array<!tsickle_ZodError_1.ZodError<?>>} */
            const unionErrors = results.map((/**
             * @param {{ctx: !tsickle_parseUtil_5.ParseContext, result: ({status: string, value: ?}|{status: string})}} result
             * @return {!tsickle_ZodError_1.ZodError<?>}
             */
            (result) => new ZodError_js_1.ZodError(result.ctx.common.issues)));
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_union,
                unionErrors,
            });
            return parseUtil_js_1.INVALID;
        }
        if (ctx.common.async) {
            return Promise.all(options.map((/**
             * @param {!ZodType<?, ?, ?>} option
             * @return {!Promise<{result: ({status: string, value: ?}|{status: string}), ctx: !tsickle_parseUtil_5.ParseContext}>}
             */
            async (option) => {
                /** @type {!tsickle_parseUtil_5.ParseContext} */
                const childCtx = {
                    ...ctx,
                    common: {
                        ...ctx.common,
                        issues: [],
                    },
                    parent: null,
                };
                return {
                    result: await option._parseAsync({
                        data: ctx.data,
                        path: ctx.path,
                        parent: childCtx,
                    }),
                    ctx: childCtx,
                };
            }))).then(handleResults);
        }
        else {
            /** @type {(undefined|{result: {status: string, value: ?}, ctx: !tsickle_parseUtil_5.ParseContext})} */
            let dirty = undefined;
            /** @type {!Array<!Array<?>>} */
            const issues = [];
            for (const option of options) {
                /** @type {!tsickle_parseUtil_5.ParseContext} */
                const childCtx = {
                    ...ctx,
                    common: {
                        ...ctx.common,
                        issues: [],
                    },
                    parent: null,
                };
                /** @type {({status: string, value: ?}|{status: string})} */
                const result = option._parseSync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: childCtx,
                });
                if (result.status === "valid") {
                    return result;
                }
                else if ((/** @type {({status: string, value: ?}|{status: string})} */ (result)).status === "dirty" && !dirty) {
                    dirty = { result, ctx: childCtx };
                }
                if (childCtx.common.issues.length) {
                    issues.push(childCtx.common.issues);
                }
            }
            if (dirty) {
                ctx.common.issues.push(...dirty.ctx.common.issues);
                return dirty.result;
            }
            /** @type {!Array<!tsickle_ZodError_1.ZodError<?>>} */
            const unionErrors = issues.map((/**
             * @param {!Array<?>} issues
             * @return {!tsickle_ZodError_1.ZodError<?>}
             */
            (issues) => new ZodError_js_1.ZodError(issues)));
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_union,
                unionErrors,
            });
            return parseUtil_js_1.INVALID;
        }
    }
    /**
     * @public
     * @return {T}
     */
    get options() {
        return this._def.options;
    }
}
exports.ZodUnion = ZodUnion;
ZodUnion.create = (/**
 * @template Options
 * @param {?} types
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodUnion<?>}
 */
(types, params) => {
    return new ZodUnion({
        options: types,
        typeName: ZodFirstPartyTypeKind.ZodUnion,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUnion<?>}
     * @public
     */
    ZodUnion.create;
}
/////////////////////////////////////////////////////
/////////////////////////////////////////////////////
//////////                                 //////////
//////////      ZodDiscriminatedUnion      //////////
//////////                                 //////////
/////////////////////////////////////////////////////
/////////////////////////////////////////////////////
/** @type {function(?): !Array<(undefined|null|string|number|bigint|symbol|boolean)>} */
const getDiscriminator = (/**
 * @template T
 * @param {?} type
 * @return {!Array<(undefined|null|string|number|bigint|symbol|boolean)>}
 */
(type) => {
    if (type instanceof ZodLazy) {
        return getDiscriminator(type.schema);
    }
    else if (type instanceof ZodEffects) {
        return getDiscriminator(type.innerType());
    }
    else if (type instanceof ZodLiteral) {
        return [type.value];
    }
    else if (type instanceof ZodEnum) {
        return type.options;
    }
    else if (type instanceof ZodNativeEnum) {
        // eslint-disable-next-line ban/ban
        return util_js_1.util.objectValues(type.enum);
    }
    else if (type instanceof ZodDefault) {
        return getDiscriminator(type._def.innerType);
    }
    else if (type instanceof ZodUndefined) {
        return [undefined];
    }
    else if (type instanceof ZodNull) {
        return [null];
    }
    else if (type instanceof ZodOptional) {
        return [undefined, ...getDiscriminator(type.unwrap())];
    }
    else if (type instanceof ZodNullable) {
        return [null, ...getDiscriminator(type.unwrap())];
    }
    else if (type instanceof ZodBranded) {
        return getDiscriminator(type.unwrap());
    }
    else if (type instanceof ZodReadonly) {
        return getDiscriminator(type.unwrap());
    }
    else if (type instanceof ZodCatch) {
        return getDiscriminator(type._def.innerType);
    }
    else {
        return [];
    }
});
/** @typedef {!ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>} */
exports.ZodDiscriminatedUnionOption;
/**
 * @record
 * @template Discriminator, Options
 * @extends {ZodTypeDef}
 */
function ZodDiscriminatedUnionDef() { }
exports.ZodDiscriminatedUnionDef = ZodDiscriminatedUnionDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {Discriminator}
     * @public
     */
    ZodDiscriminatedUnionDef.prototype.discriminator;
    /**
     * @type {Options}
     * @public
     */
    ZodDiscriminatedUnionDef.prototype.options;
    /**
     * @type {!Map<(undefined|null|string|number|bigint|symbol|boolean), !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>>}
     * @public
     */
    ZodDiscriminatedUnionDef.prototype.optionsMap;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodDiscriminatedUnionDef.prototype.typeName;
}
/**
 * @template Discriminator, Options
 * @extends {ZodType<?, !ZodDiscriminatedUnionDef<Discriminator>, ?>}
 */
class ZodDiscriminatedUnion extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.object) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.object,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {Discriminator} */
        const discriminator = this.discriminator;
        /** @type {string} */
        const discriminatorValue = ctx.data[discriminator];
        /** @type {(undefined|!ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>)} */
        const option = this.optionsMap.get(discriminatorValue);
        if (!option) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_union_discriminator,
                options: Array.from(this.optionsMap.keys()),
                path: [discriminator],
            });
            return parseUtil_js_1.INVALID;
        }
        if (ctx.common.async) {
            return (/** @type {?} */ (option._parseAsync({
                data: ctx.data,
                path: ctx.path,
                parent: ctx,
            })));
        }
        else {
            return (/** @type {?} */ (option._parseSync({
                data: ctx.data,
                path: ctx.path,
                parent: ctx,
            })));
        }
    }
    /**
     * @public
     * @return {Discriminator}
     */
    get discriminator() {
        return this._def.discriminator;
    }
    /**
     * @public
     * @return {Options}
     */
    get options() {
        return this._def.options;
    }
    /**
     * @public
     * @return {!Map<(undefined|null|string|number|bigint|symbol|boolean), !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>>}
     */
    get optionsMap() {
        return this._def.optionsMap;
    }
    /**
     * The constructor of the discriminated union schema. Its behaviour is very similar to that of the normal z.union() constructor.
     * However, it only allows a union of objects, all of which need to share a discriminator property. This property must
     * have a different value for each object in the union.
     * @public
     * @template Discriminator, Types
     * @param {Discriminator} discriminator the name of the discriminator property
     * @param {Types} options
     * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
     * @return {!ZodDiscriminatedUnion<Discriminator, Types>}
     */
    static create(discriminator, options, params) {
        // Get all the valid discriminator values
        /** @type {!Map<(undefined|null|string|number|bigint|symbol|boolean), ?>} */
        const optionsMap = new Map();
        // try {
        for (const type of options) {
            /** @type {!Array<(undefined|null|string|number|bigint|symbol|boolean)>} */
            const discriminatorValues = getDiscriminator(type.shape[discriminator]);
            if (!discriminatorValues.length) {
                throw new Error(`A discriminator value for key \`${discriminator}\` could not be extracted from all schema options`);
            }
            for (const value of discriminatorValues) {
                if (optionsMap.has(value)) {
                    throw new Error(`Discriminator property ${String(discriminator)} has duplicate value ${String(value)}`);
                }
                optionsMap.set(value, type);
            }
        }
        return new ZodDiscriminatedUnion({
            typeName: ZodFirstPartyTypeKind.ZodDiscriminatedUnion,
            discriminator,
            options,
            optionsMap,
            ...processCreateParams(params),
        });
    }
}
exports.ZodDiscriminatedUnion = ZodDiscriminatedUnion;
/**
 * @record
 * @template T, U
 * @extends {ZodTypeDef}
 */
function ZodIntersectionDef() { }
exports.ZodIntersectionDef = ZodIntersectionDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodIntersectionDef.prototype.left;
    /**
     * @type {U}
     * @public
     */
    ZodIntersectionDef.prototype.right;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodIntersectionDef.prototype.typeName;
}
/**
 * @param {?} a
 * @param {?} b
 * @return {({valid: boolean, data: ?}|{valid: boolean})}
 */
function mergeValues(a, b) {
    /** @type {string} */
    const aType = (0, util_js_1.getParsedType)(a);
    /** @type {string} */
    const bType = (0, util_js_1.getParsedType)(b);
    if (a === b) {
        return { valid: true, data: a };
    }
    else if (aType === util_js_1.ZodParsedType.object && bType === util_js_1.ZodParsedType.object) {
        /** @type {!Array<string>} */
        const bKeys = util_js_1.util.objectKeys(b);
        /** @type {!Array<string>} */
        const sharedKeys = util_js_1.util.objectKeys(a).filter((/**
         * @param {string} key
         * @return {boolean}
         */
        (key) => bKeys.indexOf(key) !== -1));
        /** @type {?} */
        const newObj = { ...a, ...b };
        for (const key of sharedKeys) {
            /** @type {({valid: boolean, data: ?}|{valid: boolean})} */
            const sharedValue = mergeValues(a[key], b[key]);
            if (!sharedValue.valid) {
                return { valid: false };
            }
            newObj[key] = (/** @type {{valid: boolean, data: ?}} */ (sharedValue)).data;
        }
        return { valid: true, data: newObj };
    }
    else if (aType === util_js_1.ZodParsedType.array && bType === util_js_1.ZodParsedType.array) {
        if (a.length !== b.length) {
            return { valid: false };
        }
        /** @type {!Array<*>} */
        const newArray = [];
        for (let index = 0; index < a.length; index++) {
            /** @type {?} */
            const itemA = a[index];
            /** @type {?} */
            const itemB = b[index];
            /** @type {({valid: boolean, data: ?}|{valid: boolean})} */
            const sharedValue = mergeValues(itemA, itemB);
            if (!sharedValue.valid) {
                return { valid: false };
            }
            newArray.push((/** @type {{valid: boolean, data: ?}} */ (sharedValue)).data);
        }
        return { valid: true, data: newArray };
    }
    else if (aType === util_js_1.ZodParsedType.date && bType === util_js_1.ZodParsedType.date && +a === +b) {
        return { valid: true, data: a };
    }
    else {
        return { valid: false };
    }
}
/**
 * @template T, U
 * @extends {ZodType<?, !ZodIntersectionDef<T>, ?>}
 */
class ZodIntersection extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        /** @type {function(({status: string, value: ?}|{status: string}), ({status: string, value: ?}|{status: string})): ({status: string, value: ?}|{status: string})} */
        const handleParsed = (/**
         * @param {({status: string, value: ?}|{status: string})} parsedLeft
         * @param {({status: string, value: ?}|{status: string})} parsedRight
         * @return {({status: string, value: ?}|{status: string})}
         */
        (parsedLeft, parsedRight) => {
            if ((0, parseUtil_js_1.isAborted)(parsedLeft) || (0, parseUtil_js_1.isAborted)(parsedRight)) {
                return parseUtil_js_1.INVALID;
            }
            /** @type {({valid: boolean, data: ?}|{valid: boolean})} */
            const merged = mergeValues((/** @type {{status: string, value: ?}} */ (parsedLeft)).value, (/** @type {{status: string, value: ?}} */ (parsedRight)).value);
            if (!merged.valid) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: ZodError_js_1.ZodIssueCode.invalid_intersection_types,
                });
                return parseUtil_js_1.INVALID;
            }
            if ((0, parseUtil_js_1.isDirty)(parsedLeft) || (0, parseUtil_js_1.isDirty)(parsedRight)) {
                status.dirty();
            }
            return { status: status.value, value: (/** @type {{valid: boolean, data: ?}} */ (merged)).data };
        });
        if (ctx.common.async) {
            return Promise.all([
                this._def.left._parseAsync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: ctx,
                }),
                this._def.right._parseAsync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: ctx,
                }),
            ]).then((/**
             * @param {?} __0
             * @return {({status: string, value: ?}|{status: string})}
             */
            ([left__tsickle_destructured_2, right__tsickle_destructured_3]) => {
                let left = /** @type {?} */ (left__tsickle_destructured_2);
                let right = /** @type {?} */ (right__tsickle_destructured_3);
                return (handleParsed(left, right));
            }));
        }
        else {
            return handleParsed(this._def.left._parseSync({
                data: ctx.data,
                path: ctx.path,
                parent: ctx,
            }), this._def.right._parseSync({
                data: ctx.data,
                path: ctx.path,
                parent: ctx,
            }));
        }
    }
}
exports.ZodIntersection = ZodIntersection;
ZodIntersection.create = (/**
 * @template TSchema, USchema
 * @param {?} left
 * @param {?} right
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodIntersection<?, ?>}
 */
(left, right, params) => {
    return new ZodIntersection({
        left: left,
        right: right,
        typeName: ZodFirstPartyTypeKind.ZodIntersection,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodIntersection<?, ?>}
     * @public
     */
    ZodIntersection.create;
}
/** @typedef {!Array<?>} */
exports.ZodTupleItems;
/** @typedef {?} */
exports.AssertArray;
/** @typedef {?} */
exports.OutputTypeOfTuple;
/** @typedef {?} */
exports.OutputTypeOfTupleWithRest;
/** @typedef {?} */
exports.InputTypeOfTuple;
/** @typedef {?} */
exports.InputTypeOfTupleWithRest;
/**
 * @record
 * @template T, Rest
 * @extends {ZodTypeDef}
 */
function ZodTupleDef() { }
exports.ZodTupleDef = ZodTupleDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodTupleDef.prototype.items;
    /**
     * @type {Rest}
     * @public
     */
    ZodTupleDef.prototype.rest;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodTupleDef.prototype.typeName;
}
/** @typedef {!ZodTuple<!Array<?>, (null|!ZodType<?, ?, ?>)>} */
exports.AnyZodTuple;
// type ZodTupleItems = [ZodTypeAny, ...ZodTypeAny[]];
/**
 * @template T, Rest
 * @extends {ZodType<?, !ZodTupleDef<T>, ?>}
 */
class ZodTuple extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.array) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.array,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        if (ctx.data.length < (/** @type {!Array<?>} */ (this._def.items)).length) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.too_small,
                minimum: (/** @type {!Array<?>} */ (this._def.items)).length,
                inclusive: true,
                exact: false,
                type: "array",
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {Rest} */
        const rest = this._def.rest;
        if (!rest && ctx.data.length > (/** @type {!Array<?>} */ (this._def.items)).length) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.too_big,
                maximum: (/** @type {!Array<?>} */ (this._def.items)).length,
                inclusive: true,
                exact: false,
                type: "array",
            });
            status.dirty();
        }
        /** @type {!Array<(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})>} */
        const items = ((/** @type {!Array<?>} */ ([...ctx.data])))
            .map((/**
         * @param {?} item
         * @param {number} itemIndex
         * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
         */
        (item, itemIndex) => {
            /** @type {!ZodType<?, ?, ?>} */
            const schema = this._def.items[itemIndex] || this._def.rest;
            if (!schema)
                return (/** @type {({status: string, value: ?}|{status: string})} */ ((/** @type {?} */ (null))));
            return schema._parse(new ParseInputLazyPath(ctx, item, ctx.path, itemIndex));
        }))
            .filter((/**
         * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} x
         * @return {boolean}
         */
        (x) => !!x));
        if (ctx.common.async) {
            return Promise.all(items).then((/**
             * @param {!Array<({status: string, value: ?}|{status: string})>} results
             * @return {({status: string, value: ?}|{status: string})}
             */
            (results) => {
                return parseUtil_js_1.ParseStatus.mergeArray(status, results);
            }));
        }
        else {
            return parseUtil_js_1.ParseStatus.mergeArray(status, (/** @type {!Array<({status: string, value: ?}|{status: string})>} */ (items)));
        }
    }
    /**
     * @public
     * @return {T}
     */
    get items() {
        return this._def.items;
    }
    /**
     * @public
     * @template RestSchema
     * @param {RestSchema} rest
     * @return {!ZodTuple<T, RestSchema>}
     */
    rest(rest) {
        return new ZodTuple({
            ...this._def,
            rest,
        });
    }
}
exports.ZodTuple = ZodTuple;
ZodTuple.create = (/**
 * @template Items
 * @param {?} schemas
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodTuple<?, null>}
 */
(schemas, params) => {
    if (!Array.isArray(schemas)) {
        throw new Error("You must pass an array of schemas to z.tuple([ ... ])");
    }
    return new ZodTuple({
        items: schemas,
        typeName: ZodFirstPartyTypeKind.ZodTuple,
        rest: null,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodTuple<?, null>}
     * @public
     */
    ZodTuple.create;
}
/**
 * @record
 * @template Key, Value
 * @extends {ZodTypeDef}
 */
function ZodRecordDef() { }
exports.ZodRecordDef = ZodRecordDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {Value}
     * @public
     */
    ZodRecordDef.prototype.valueType;
    /**
     * @type {Key}
     * @public
     */
    ZodRecordDef.prototype.keyType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodRecordDef.prototype.typeName;
}
/** @typedef {!ZodType<(string|number|symbol), ?, ?>} */
exports.KeySchema;
/** @typedef {?} */
exports.RecordType;
/**
 * @template Key, Value
 * @extends {ZodType<?, !ZodRecordDef<Key>, ?>}
 */
class ZodRecord extends ZodType {
    /**
     * @public
     * @return {Key}
     */
    get keySchema() {
        return this._def.keyType;
    }
    /**
     * @public
     * @return {Value}
     */
    get valueSchema() {
        return this._def.valueType;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.object) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.object,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {!Array<{key: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), value: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), alwaysSet: boolean}>} */
        const pairs = [];
        /** @type {Key} */
        const keyType = this._def.keyType;
        /** @type {Value} */
        const valueType = this._def.valueType;
        for (const key in ctx.data) {
            pairs.push({
                key: keyType._parse(new ParseInputLazyPath(ctx, key, ctx.path, key)),
                value: valueType._parse(new ParseInputLazyPath(ctx, ctx.data[key], ctx.path, key)),
                alwaysSet: key in ctx.data,
            });
        }
        if (ctx.common.async) {
            return parseUtil_js_1.ParseStatus.mergeObjectAsync(status, pairs);
        }
        else {
            return parseUtil_js_1.ParseStatus.mergeObjectSync(status, (/** @type {?} */ (pairs)));
        }
    }
    /**
     * @public
     * @return {Value}
     */
    get element() {
        return this._def.valueType;
    }
    /**
     * @public
     * @param {?} first
     * @param {?=} second
     * @param {?=} third
     * @return {!ZodRecord<?, ?>}
     */
    static create(first, second, third) {
        if (second instanceof ZodType) {
            return new ZodRecord({
                keyType: first,
                valueType: second,
                typeName: ZodFirstPartyTypeKind.ZodRecord,
                ...processCreateParams(third),
            });
        }
        return new ZodRecord({
            keyType: ZodString.create(),
            valueType: first,
            typeName: ZodFirstPartyTypeKind.ZodRecord,
            ...processCreateParams(second),
        });
    }
}
exports.ZodRecord = ZodRecord;
/**
 * @record
 * @template Key, Value
 * @extends {ZodTypeDef}
 */
function ZodMapDef() { }
exports.ZodMapDef = ZodMapDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {Value}
     * @public
     */
    ZodMapDef.prototype.valueType;
    /**
     * @type {Key}
     * @public
     */
    ZodMapDef.prototype.keyType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodMapDef.prototype.typeName;
}
/**
 * @template Key, Value
 * @extends {ZodType<!Map<?>, !ZodMapDef<Key>, !Map<?>>}
 */
class ZodMap extends ZodType {
    /**
     * @public
     * @return {Key}
     */
    get keySchema() {
        return this._def.keyType;
    }
    /**
     * @public
     * @return {Value}
     */
    get valueSchema() {
        return this._def.valueType;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.map) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.map,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {Key} */
        const keyType = this._def.keyType;
        /** @type {Value} */
        const valueType = this._def.valueType;
        /** @type {!Array<{key: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), value: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}>} */
        const pairs = [...((/** @type {!Map<*, *>} */ (ctx.data))).entries()].map((/**
         * @param {!Array<?>} __0
         * @param {number} index
         * @return {{key: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string}), value: (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}}
         */
        ([key__tsickle_destructured_4, value__tsickle_destructured_5], index) => {
            let key = /** @type {*} */ (key__tsickle_destructured_4);
            let value = /** @type {*} */ (value__tsickle_destructured_5);
            return {
                key: keyType._parse(new ParseInputLazyPath(ctx, key, ctx.path, [index, "key"])),
                value: valueType._parse(new ParseInputLazyPath(ctx, value, ctx.path, [index, "value"])),
            };
        }));
        if (ctx.common.async) {
            /** @type {!Map<?, ?>} */
            const finalMap = new Map();
            return Promise.resolve().then((/**
             * @return {!Promise<({status: string}|{status: string, value: !Map<?, ?>})>}
             */
            async () => {
                for (const pair of pairs) {
                    /** @type {({status: string, value: ?}|{status: string})} */
                    const key = await pair.key;
                    /** @type {({status: string, value: ?}|{status: string})} */
                    const value = await pair.value;
                    if (key.status === "aborted" || value.status === "aborted") {
                        return parseUtil_js_1.INVALID;
                    }
                    if ((/** @type {{status: string, value: ?}} */ (key)).status === "dirty" || (/** @type {{status: string, value: ?}} */ (value)).status === "dirty") {
                        status.dirty();
                    }
                    finalMap.set((/** @type {{status: string, value: ?}} */ (key)).value, (/** @type {{status: string, value: ?}} */ (value)).value);
                }
                return { status: status.value, value: finalMap };
            }));
        }
        else {
            /** @type {!Map<?, ?>} */
            const finalMap = new Map();
            for (const pair of pairs) {
                /** @type {({status: string, value: ?}|{status: string})} */
                const key = (/** @type {({status: string, value: ?}|{status: string})} */ (pair.key));
                /** @type {({status: string, value: ?}|{status: string})} */
                const value = (/** @type {({status: string, value: ?}|{status: string})} */ (pair.value));
                if (key.status === "aborted" || value.status === "aborted") {
                    return parseUtil_js_1.INVALID;
                }
                if ((/** @type {{status: string, value: ?}} */ (key)).status === "dirty" || (/** @type {{status: string, value: ?}} */ (value)).status === "dirty") {
                    status.dirty();
                }
                finalMap.set((/** @type {{status: string, value: ?}} */ (key)).value, (/** @type {{status: string, value: ?}} */ (value)).value);
            }
            return { status: status.value, value: finalMap };
        }
    }
}
exports.ZodMap = ZodMap;
ZodMap.create = (/**
 * @template KeySchema, ValueSchema
 * @param {?} keyType
 * @param {?} valueType
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodMap<?, ?>}
 */
(keyType, valueType, params) => {
    return new ZodMap({
        valueType,
        keyType,
        typeName: ZodFirstPartyTypeKind.ZodMap,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodMap<?, ?>}
     * @public
     */
    ZodMap.create;
}
/**
 * @record
 * @template Value
 * @extends {ZodTypeDef}
 */
function ZodSetDef() { }
exports.ZodSetDef = ZodSetDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {Value}
     * @public
     */
    ZodSetDef.prototype.valueType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodSetDef.prototype.typeName;
    /**
     * @type {(null|{value: number, message: (undefined|string)})}
     * @public
     */
    ZodSetDef.prototype.minSize;
    /**
     * @type {(null|{value: number, message: (undefined|string)})}
     * @public
     */
    ZodSetDef.prototype.maxSize;
}
/**
 * @template Value
 * @extends {ZodType<!Set, !ZodSetDef, !Set>}
 */
class ZodSet extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.set) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.set,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {!ZodSetDef<Value>} */
        const def = this._def;
        if (def.minSize !== null) {
            if (ctx.data.size < def.minSize.value) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: ZodError_js_1.ZodIssueCode.too_small,
                    minimum: def.minSize.value,
                    type: "set",
                    inclusive: true,
                    exact: false,
                    message: def.minSize.message,
                });
                status.dirty();
            }
        }
        if (def.maxSize !== null) {
            if (ctx.data.size > def.maxSize.value) {
                (0, parseUtil_js_1.addIssueToContext)(ctx, {
                    code: ZodError_js_1.ZodIssueCode.too_big,
                    maximum: def.maxSize.value,
                    type: "set",
                    inclusive: true,
                    exact: false,
                    message: def.maxSize.message,
                });
                status.dirty();
            }
        }
        /** @type {Value} */
        const valueType = this._def.valueType;
        /**
         * @param {!Array<({status: string, value: ?}|{status: string})>} elements
         * @return {({status: string}|{status: string, value: !Set<*>})}
         */
        function finalizeSet(elements) {
            /** @type {!Set<*>} */
            const parsedSet = new Set();
            for (const element of elements) {
                if (element.status === "aborted")
                    return parseUtil_js_1.INVALID;
                if ((/** @type {{status: string, value: ?}} */ (element)).status === "dirty")
                    status.dirty();
                parsedSet.add((/** @type {{status: string, value: ?}} */ (element)).value);
            }
            return { status: status.value, value: parsedSet };
        }
        /** @type {!Array<(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})>} */
        const elements = [...((/** @type {!Set<*>} */ (ctx.data))).values()].map((/**
         * @param {*} item
         * @param {number} i
         * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
         */
        (item, i) => valueType._parse(new ParseInputLazyPath(ctx, item, ctx.path, i))));
        if (ctx.common.async) {
            return Promise.all(elements).then((/**
             * @param {!Array<({status: string, value: ?}|{status: string})>} elements
             * @return {({status: string}|{status: string, value: !Set<*>})}
             */
            (elements) => finalizeSet(elements)));
        }
        else {
            return finalizeSet((/** @type {!Array<({status: string, value: ?}|{status: string})>} */ (elements)));
        }
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} minSize
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    min(minSize, message) {
        return (/** @type {?} */ (new ZodSet({
            ...(/** @type {!ZodSet} */ (this))._def,
            minSize: { value: minSize, message: errorUtil_js_1.errorUtil.toString(message) },
        })));
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} maxSize
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    max(maxSize, message) {
        return (/** @type {?} */ (new ZodSet({
            ...(/** @type {!ZodSet} */ (this))._def,
            maxSize: { value: maxSize, message: errorUtil_js_1.errorUtil.toString(message) },
        })));
    }
    /**
     * @public
     * @template THIS
     * @this {THIS}
     * @param {number} size
     * @param {(undefined|string|?)=} message
     * @return {THIS}
     */
    size(size, message) {
        return (/** @type {?} */ ((/** @type {!ZodSet} */ (this)).min(size, message).max(size, message)));
    }
    /**
     * @public
     * @param {(undefined|string|?)=} message
     * @return {!ZodSet}
     */
    nonempty(message) {
        return (/** @type {?} */ (this.min(1, message)));
    }
}
exports.ZodSet = ZodSet;
ZodSet.create = (/**
 * @template ValueSchema
 * @param {?} valueType
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodSet<?>}
 */
(valueType, params) => {
    return new ZodSet({
        valueType,
        minSize: null,
        maxSize: null,
        typeName: ZodFirstPartyTypeKind.ZodSet,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodSet<?>}
     * @public
     */
    ZodSet.create;
}
/**
 * @record
 * @template Args, Returns
 * @extends {ZodTypeDef}
 */
function ZodFunctionDef() { }
exports.ZodFunctionDef = ZodFunctionDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {Args}
     * @public
     */
    ZodFunctionDef.prototype.args;
    /**
     * @type {Returns}
     * @public
     */
    ZodFunctionDef.prototype.returns;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodFunctionDef.prototype.typeName;
}
/** @typedef {?} */
exports.OuterTypeOfFunction;
/** @typedef {?} */
exports.InnerTypeOfFunction;
/**
 * @template Args, Returns
 * @extends {ZodType<?, !ZodFunctionDef<Args>, ?>}
 */
class ZodFunction extends ZodType {
    constructor() {
        super(...arguments);
        this.validate = this.implement;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.function) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.function,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /**
         * @param {?} args
         * @param {!tsickle_ZodError_1.ZodError<?>} error
         * @return {?}
         */
        function makeArgsIssue(args, error) {
            return (0, parseUtil_js_1.makeIssue)({
                data: args,
                path: ctx.path,
                errorMaps: [ctx.common.contextualErrorMap, ctx.schemaErrorMap, (0, errors_js_1.getErrorMap)(), errors_js_1.defaultErrorMap].filter((/**
                 * @param {(undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})} x
                 * @return {boolean}
                 */
                (x) => !!x)),
                issueData: {
                    code: ZodError_js_1.ZodIssueCode.invalid_arguments,
                    argumentsError: error,
                },
            });
        }
        /**
         * @param {?} returns
         * @param {!tsickle_ZodError_1.ZodError<?>} error
         * @return {?}
         */
        function makeReturnsIssue(returns, error) {
            return (0, parseUtil_js_1.makeIssue)({
                data: returns,
                path: ctx.path,
                errorMaps: [ctx.common.contextualErrorMap, ctx.schemaErrorMap, (0, errors_js_1.getErrorMap)(), errors_js_1.defaultErrorMap].filter((/**
                 * @param {(undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})} x
                 * @return {boolean}
                 */
                (x) => !!x)),
                issueData: {
                    code: ZodError_js_1.ZodIssueCode.invalid_return_type,
                    returnTypeError: error,
                },
            });
        }
        /** @type {{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string})}} */
        const params = { errorMap: ctx.common.contextualErrorMap };
        /** @type {?} */
        const fn = ctx.data;
        if (this._def.returns instanceof ZodPromise) {
            // Would love a way to avoid disabling this rule, but we need
            // an alias (using an arrow function was what caused 2651).
            // eslint-disable-next-line @typescript-eslint/no-this-alias
            /** @type {!ZodFunction} */
            const me = this;
            return (0, parseUtil_js_1.OK)((/**
             * @this {?}
             * @param {...?} args
             * @return {!Promise<?>}
             */
            async function (...args) {
                /** @type {!tsickle_ZodError_1.ZodError<?>} */
                const error = new ZodError_js_1.ZodError([]);
                /** @type {!Array<?>} */
                const parsedArgs = await me._def.args.parseAsync(args, params).catch((/**
                 * @param {?} e
                 * @return {?}
                 */
                (e) => {
                    error.addIssue(makeArgsIssue(args, e));
                    throw error;
                }));
                /** @type {*} */
                const result = await Reflect.apply(fn, this, (/** @type {?} */ (parsedArgs)));
                /** @type {?} */
                const parsedReturns = await ((/** @type {!ZodPromise<!ZodType<?, ?, ?>>} */ ((/** @type {*} */ (me._def.returns)))))._def.type
                    .parseAsync(result, params)
                    .catch((/**
                 * @param {?} e
                 * @return {?}
                 */
                (e) => {
                    error.addIssue(makeReturnsIssue(result, e));
                    throw error;
                }));
                return parsedReturns;
            }));
        }
        else {
            // Would love a way to avoid disabling this rule, but we need
            // an alias (using an arrow function was what caused 2651).
            // eslint-disable-next-line @typescript-eslint/no-this-alias
            /** @type {!ZodFunction} */
            const me = this;
            return (/** @type {?} */ ((0, parseUtil_js_1.OK)((/**
             * @this {?}
             * @param {...?} args
             * @return {?}
             */
            function (...args) {
                /** @type {({success: boolean, error: !tsickle_ZodError_1.ZodError<!Array<?>>, data: undefined}|{success: boolean, data: !Array<?>, error: undefined})} */
                const parsedArgs = me._def.args.safeParse(args, params);
                if (!parsedArgs.success) {
                    throw new ZodError_js_1.ZodError([makeArgsIssue(args, (/** @type {{success: boolean, error: !tsickle_ZodError_1.ZodError<!Array<?>>, data: undefined}} */ (parsedArgs)).error)]);
                }
                /** @type {*} */
                const result = Reflect.apply(fn, this, (/** @type {{success: boolean, data: !Array<?>, error: undefined}} */ (parsedArgs)).data);
                /** @type {({success: boolean, error: !tsickle_ZodError_1.ZodError<?>, data: undefined}|{success: boolean, data: ?, error: undefined})} */
                const parsedReturns = me._def.returns.safeParse(result, params);
                if (!parsedReturns.success) {
                    throw new ZodError_js_1.ZodError([makeReturnsIssue(result, (/** @type {{success: boolean, error: !tsickle_ZodError_1.ZodError<?>, data: undefined}} */ (parsedReturns)).error)]);
                }
                return (/** @type {{success: boolean, data: ?, error: undefined}} */ (parsedReturns)).data;
            }))));
        }
    }
    /**
     * @public
     * @return {Args}
     */
    parameters() {
        return this._def.args;
    }
    /**
     * @public
     * @return {Returns}
     */
    returnType() {
        return this._def.returns;
    }
    /**
     * @public
     * @template Items
     * @param {...?} items
     * @return {!ZodFunction<!ZodTuple<Items, !ZodUnknown>, Returns>}
     */
    args(...items) {
        return new ZodFunction({
            ...this._def,
            args: (/** @type {?} */ (ZodTuple.create(items).rest(ZodUnknown.create()))),
        });
    }
    /**
     * @public
     * @template NewReturnType
     * @param {NewReturnType} returnType
     * @return {!ZodFunction<Args, NewReturnType>}
     */
    returns(returnType) {
        return new ZodFunction({
            ...this._def,
            returns: returnType,
        });
    }
    /**
     * @public
     * @template F
     * @param {?} func
     * @return {?}
     */
    implement(func) {
        /** @type {?} */
        const validatedFunc = this.parse(func);
        return (/** @type {?} */ (validatedFunc));
    }
    /**
     * @public
     * @param {?} func
     * @return {?}
     */
    strictImplement(func) {
        /** @type {?} */
        const validatedFunc = this.parse(func);
        return (/** @type {?} */ (validatedFunc));
    }
    /**
     * @public
     * @param {(undefined|!ZodTuple<!Array<?>, (null|!ZodType<?, ?, ?>)>)=} args
     * @param {(undefined|!ZodType<?, ?, ?>)=} returns
     * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
     * @return {?}
     */
    static create(args, returns, params) {
        return (/** @type {?} */ (new ZodFunction({
            args: (/** @type {?} */ ((args ? args : ZodTuple.create([]).rest(ZodUnknown.create())))),
            returns: returns || ZodUnknown.create(),
            typeName: ZodFirstPartyTypeKind.ZodFunction,
            ...processCreateParams(params),
        })));
    }
}
exports.ZodFunction = ZodFunction;
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?): ?}
     * @public
     */
    ZodFunction.prototype.validate;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodLazyDef() { }
exports.ZodLazyDef = ZodLazyDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(): T}
     * @public
     */
    ZodLazyDef.prototype.getter;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodLazyDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<?, !ZodLazyDef, ?>}
 */
class ZodLazy extends ZodType {
    /**
     * @public
     * @return {T}
     */
    get schema() {
        return this._def.getter();
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        /** @type {T} */
        const lazySchema = this._def.getter();
        return lazySchema._parse({ data: ctx.data, path: ctx.path, parent: ctx });
    }
}
exports.ZodLazy = ZodLazy;
ZodLazy.create = (/**
 * @template Inner
 * @param {function(): ?} getter
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodLazy<?>}
 */
(getter, params) => {
    return new ZodLazy({
        getter: getter,
        typeName: ZodFirstPartyTypeKind.ZodLazy,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(function(): ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodLazy<?>}
     * @public
     */
    ZodLazy.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodLiteralDef() { }
exports.ZodLiteralDef = ZodLiteralDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodLiteralDef.prototype.value;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodLiteralDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<T, !ZodLiteralDef, T>}
 */
class ZodLiteral extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        if (input.data !== this._def.value) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                received: ctx.data,
                code: ZodError_js_1.ZodIssueCode.invalid_literal,
                expected: this._def.value,
            });
            return parseUtil_js_1.INVALID;
        }
        return { status: "valid", value: input.data };
    }
    /**
     * @public
     * @return {T}
     */
    get value() {
        return this._def.value;
    }
}
exports.ZodLiteral = ZodLiteral;
ZodLiteral.create = (/**
 * @template Value
 * @param {?} value
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodLiteral<?>}
 */
(value, params) => {
    return new ZodLiteral({
        value: value,
        typeName: ZodFirstPartyTypeKind.ZodLiteral,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodLiteral<?>}
     * @public
     */
    ZodLiteral.create;
}
/** @typedef {(number|string|symbol)} */
exports.ArrayKeys;
/** @typedef {?} */
exports.Indices;
/** @typedef {!Array<?>} */
exports.EnumValues;
/** @typedef {?} */
exports.Values;
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodEnumDef() { }
exports.ZodEnumDef = ZodEnumDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodEnumDef.prototype.values;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodEnumDef.prototype.typeName;
}
/** @typedef {?} */
exports.Writeable;
/** @typedef {?} */
exports.FilterEnum;
/** @typedef {?} */
exports.typecast;
/**
 * @param {!Array<?>} values
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodEnum<!Array<?>>}
 */
function createZodEnum(values, params) {
    return new ZodEnum({
        values,
        typeName: ZodFirstPartyTypeKind.ZodEnum,
        ...processCreateParams(params),
    });
}
/**
 * @template T
 * @extends {ZodType<?, !ZodEnumDef, ?>}
 */
class ZodEnum extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        if (typeof input.data !== "string") {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            /** @type {T} */
            const expectedValues = this._def.values;
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                expected: (/** @type {string} */ (util_js_1.util.joinValues(expectedValues))),
                received: ctx.parsedType,
                code: ZodError_js_1.ZodIssueCode.invalid_type,
            });
            return parseUtil_js_1.INVALID;
        }
        if (!this._cache) {
            this._cache = new Set(this._def.values);
        }
        if (!this._cache.has(input.data)) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            /** @type {T} */
            const expectedValues = this._def.values;
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                received: ctx.data,
                code: ZodError_js_1.ZodIssueCode.invalid_enum_value,
                options: expectedValues,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
    /**
     * @public
     * @return {T}
     */
    get options() {
        return this._def.values;
    }
    /**
     * @public
     * @return {?}
     */
    get enum() {
        /** @type {?} */
        const enumValues = {};
        for (const val of this._def.values) {
            enumValues[val] = val;
        }
        return enumValues;
    }
    /**
     * @public
     * @return {?}
     */
    get Values() {
        /** @type {?} */
        const enumValues = {};
        for (const val of this._def.values) {
            enumValues[val] = val;
        }
        return enumValues;
    }
    /**
     * @public
     * @return {?}
     */
    get Enum() {
        /** @type {?} */
        const enumValues = {};
        for (const val of this._def.values) {
            enumValues[val] = val;
        }
        return enumValues;
    }
    /**
     * @public
     * @template ToExtract
     * @param {ToExtract} values
     * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} newDef
     * @return {!ZodEnum<?>}
     */
    extract(values, newDef = this._def) {
        return (/** @type {?} */ (ZodEnum.create(values, {
            ...this._def,
            ...newDef,
        })));
    }
    /**
     * @public
     * @template ToExclude
     * @param {ToExclude} values
     * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} newDef
     * @return {!ZodEnum<?>}
     */
    exclude(values, newDef = this._def) {
        return (/** @type {?} */ (ZodEnum.create((/** @type {?} */ (this.options.filter((/**
         * @param {string} opt
         * @return {boolean}
         */
        (opt) => !values.includes(opt))))), {
            ...this._def,
            ...newDef,
        })));
    }
}
exports.ZodEnum = ZodEnum;
ZodEnum.create = createZodEnum;
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(!Array<?>, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEnum<!Array<?>>}
     * @public
     */
    ZodEnum.create;
    /**
     * @type {(undefined|!Set<?>)}
     * @public
     */
    ZodEnum.prototype._cache;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodNativeEnumDef() { }
exports.ZodNativeEnumDef = ZodNativeEnumDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodNativeEnumDef.prototype.values;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNativeEnumDef.prototype.typeName;
}
/** @typedef {!Object<string,(string|number)>} */
exports.EnumLike;
/**
 * @template T
 * @extends {ZodType<?, !ZodNativeEnumDef, ?>}
 */
class ZodNativeEnum extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {!Array<?>} */
        const nativeEnumValues = util_js_1.util.getValidEnumValues(this._def.values);
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const ctx = this._getOrReturnCtx(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.string && ctx.parsedType !== util_js_1.ZodParsedType.number) {
            /** @type {!Array<?>} */
            const expectedValues = util_js_1.util.objectValues(nativeEnumValues);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                expected: (/** @type {string} */ (util_js_1.util.joinValues(expectedValues))),
                received: ctx.parsedType,
                code: ZodError_js_1.ZodIssueCode.invalid_type,
            });
            return parseUtil_js_1.INVALID;
        }
        if (!this._cache) {
            this._cache = new Set(util_js_1.util.getValidEnumValues(this._def.values));
        }
        if (!this._cache.has(input.data)) {
            /** @type {!Array<?>} */
            const expectedValues = util_js_1.util.objectValues(nativeEnumValues);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                received: ctx.data,
                code: ZodError_js_1.ZodIssueCode.invalid_enum_value,
                options: expectedValues,
            });
            return parseUtil_js_1.INVALID;
        }
        return (0, parseUtil_js_1.OK)(input.data);
    }
    /**
     * @public
     * @return {T}
     */
    get enum() {
        return this._def.values;
    }
}
exports.ZodNativeEnum = ZodNativeEnum;
ZodNativeEnum.create = (/**
 * @template Elements
 * @param {?} values
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodNativeEnum<?>}
 */
(values, params) => {
    return new ZodNativeEnum({
        values: values,
        typeName: ZodFirstPartyTypeKind.ZodNativeEnum,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNativeEnum<?>}
     * @public
     */
    ZodNativeEnum.create;
    /**
     * @type {(undefined|!Set<?>)}
     * @public
     */
    ZodNativeEnum.prototype._cache;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodPromiseDef() { }
exports.ZodPromiseDef = ZodPromiseDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodPromiseDef.prototype.type;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodPromiseDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<!Promise, !ZodPromiseDef, !Promise>}
 */
class ZodPromise extends ZodType {
    /**
     * @public
     * @return {T}
     */
    unwrap() {
        return this._def.type;
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        if (ctx.parsedType !== util_js_1.ZodParsedType.promise && ctx.common.async === false) {
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.promise,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        /** @type {?} */
        const promisified = ctx.parsedType === util_js_1.ZodParsedType.promise ? ctx.data : Promise.resolve(ctx.data);
        return (0, parseUtil_js_1.OK)(promisified.then((/**
         * @param {?} data
         * @return {!Promise<?>}
         */
        (data) => {
            return this._def.type.parseAsync(data, {
                path: ctx.path,
                errorMap: ctx.common.contextualErrorMap,
            });
        })));
    }
}
exports.ZodPromise = ZodPromise;
ZodPromise.create = (/**
 * @template Inner
 * @param {?} schema
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodPromise<?>}
 */
(schema, params) => {
    return new ZodPromise({
        type: schema,
        typeName: ZodFirstPartyTypeKind.ZodPromise,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodPromise<?>}
     * @public
     */
    ZodPromise.create;
}
/** @typedef {function(?, !RefinementCtx): ?} */
exports.Refinement;
/** @typedef {function(?, !RefinementCtx): (void|!Promise<void>)} */
exports.SuperRefinement;
/** @typedef {{type: string, refinement: function(?, !RefinementCtx): ?}} */
exports.RefinementEffect;
/** @typedef {{type: string, transform: function(?, !RefinementCtx): ?}} */
exports.TransformEffect;
/** @typedef {{type: string, transform: function(?, !RefinementCtx): ?}} */
exports.PreprocessEffect;
/** @typedef {({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?})} */
exports.Effect;
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodEffectsDef() { }
exports.ZodEffectsDef = ZodEffectsDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodEffectsDef.prototype.schema;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodEffectsDef.prototype.typeName;
    /**
     * @type {({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?})}
     * @public
     */
    ZodEffectsDef.prototype.effect;
}
/**
 * @template T, Output, Input
 * @extends {ZodType<Output, !ZodEffectsDef, Input>}
 */
class ZodEffects extends ZodType {
    /**
     * @public
     * @return {T}
     */
    innerType() {
        return this._def.schema;
    }
    /**
     * @public
     * @return {T}
     */
    sourceType() {
        return this._def.schema._def.typeName === ZodFirstPartyTypeKind.ZodEffects
            ? ((/** @type {!ZodEffects<T, ?, ?>} */ ((/** @type {*} */ (this._def.schema))))).sourceType()
            : ((/** @type {T} */ (this._def.schema)));
    }
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        /** @type {({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?})} */
        const effect = this._def.effect || null;
        /** @type {!RefinementCtx} */
        const checkCtx = {
            addIssue: (/**
             * @param {?} arg
             * @return {void}
             */
            (arg) => {
                (0, parseUtil_js_1.addIssueToContext)(ctx, arg);
                if (arg.fatal) {
                    status.abort();
                }
                else {
                    status.dirty();
                }
            }),
            /**
             * @public
             * @return {!Array<(string|number)>}
             */
            get path() {
                return ctx.path;
            },
        };
        checkCtx.addIssue = checkCtx.addIssue.bind(checkCtx);
        if (effect.type === "preprocess") {
            /** @type {?} */
            const processed = (/** @type {{type: string, transform: function(?, !RefinementCtx): ?}} */ (effect)).transform(ctx.data, checkCtx);
            if (ctx.common.async) {
                return Promise.resolve(processed).then((/**
                 * @param {?} processed
                 * @return {!Promise<({status: string, value: ?}|{status: string})>}
                 */
                async (processed) => {
                    if (status.value === "aborted")
                        return parseUtil_js_1.INVALID;
                    /** @type {({status: string, value: ?}|{status: string})} */
                    const result = await this._def.schema._parseAsync({
                        data: processed,
                        path: ctx.path,
                        parent: ctx,
                    });
                    if (result.status === "aborted")
                        return parseUtil_js_1.INVALID;
                    if ((/** @type {{status: string, value: ?}} */ (result)).status === "dirty")
                        return (0, parseUtil_js_1.DIRTY)((/** @type {{status: string, value: ?}} */ (result)).value);
                    if (status.value === "dirty")
                        return (0, parseUtil_js_1.DIRTY)((/** @type {{status: string, value: ?}} */ (result)).value);
                    return result;
                }));
            }
            else {
                if (status.value === "aborted")
                    return parseUtil_js_1.INVALID;
                /** @type {({status: string, value: ?}|{status: string})} */
                const result = this._def.schema._parseSync({
                    data: processed,
                    path: ctx.path,
                    parent: ctx,
                });
                if (result.status === "aborted")
                    return parseUtil_js_1.INVALID;
                if ((/** @type {{status: string, value: ?}} */ (result)).status === "dirty")
                    return (0, parseUtil_js_1.DIRTY)((/** @type {{status: string, value: ?}} */ (result)).value);
                if (status.value === "dirty")
                    return (0, parseUtil_js_1.DIRTY)((/** @type {{status: string, value: ?}} */ (result)).value);
                return result;
            }
        }
        if ((/** @type {({type: string, refinement: function(?, !RefinementCtx): ?}|{type: string, transform: function(?, !RefinementCtx): ?})} */ (effect)).type === "refinement") {
            /** @type {function(*): ?} */
            const executeRefinement = (/**
             * @param {*} acc
             * @return {?}
             */
            (acc) => {
                /** @type {?} */
                const result = (/** @type {{type: string, refinement: function(?, !RefinementCtx): ?}} */ (effect)).refinement(acc, checkCtx);
                if (ctx.common.async) {
                    return Promise.resolve(result);
                }
                if (result instanceof Promise) {
                    throw new Error("Async refinement encountered during synchronous parse operation. Use .parseAsync instead.");
                }
                return acc;
            });
            if (ctx.common.async === false) {
                /** @type {({status: string, value: ?}|{status: string})} */
                const inner = this._def.schema._parseSync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: ctx,
                });
                if (inner.status === "aborted")
                    return parseUtil_js_1.INVALID;
                if ((/** @type {{status: string, value: ?}} */ (inner)).status === "dirty")
                    status.dirty();
                // return value is ignored
                executeRefinement((/** @type {{status: string, value: ?}} */ (inner)).value);
                return { status: status.value, value: (/** @type {{status: string, value: ?}} */ (inner)).value };
            }
            else {
                return this._def.schema._parseAsync({ data: ctx.data, path: ctx.path, parent: ctx }).then((/**
                 * @param {({status: string, value: ?}|{status: string})} inner
                 * @return {?}
                 */
                (inner) => {
                    if (inner.status === "aborted")
                        return parseUtil_js_1.INVALID;
                    if ((/** @type {{status: string, value: ?}} */ (inner)).status === "dirty")
                        status.dirty();
                    return executeRefinement((/** @type {{status: string, value: ?}} */ (inner)).value).then((/**
                     * @return {{status: string, value: ?}}
                     */
                    () => {
                        return { status: status.value, value: (/** @type {{status: string, value: ?}} */ (inner)).value };
                    }));
                }));
            }
        }
        if ((/** @type {{type: string, transform: function(?, !RefinementCtx): ?}} */ (effect)).type === "transform") {
            if (ctx.common.async === false) {
                /** @type {({status: string, value: ?}|{status: string})} */
                const base = this._def.schema._parseSync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: ctx,
                });
                if (!(0, parseUtil_js_1.isValid)(base))
                    return parseUtil_js_1.INVALID;
                /** @type {?} */
                const result = (/** @type {{type: string, transform: function(?, !RefinementCtx): ?}} */ (effect)).transform((/** @type {{status: string, value: ?}} */ (base)).value, checkCtx);
                if (result instanceof Promise) {
                    throw new Error(`Asynchronous transform encountered during synchronous parse operation. Use .parseAsync instead.`);
                }
                return { status: status.value, value: result };
            }
            else {
                return this._def.schema._parseAsync({ data: ctx.data, path: ctx.path, parent: ctx }).then((/**
                 * @param {({status: string, value: ?}|{status: string})} base
                 * @return {({status: string}|!Promise<({status: string, value: ?}|{status: string})>)}
                 */
                (base) => {
                    if (!(0, parseUtil_js_1.isValid)(base))
                        return parseUtil_js_1.INVALID;
                    return Promise.resolve((/** @type {{type: string, transform: function(?, !RefinementCtx): ?}} */ (effect)).transform((/** @type {{status: string, value: ?}} */ (base)).value, checkCtx)).then((/**
                     * @param {?} result
                     * @return {{status: string, value: ?}}
                     */
                    (result) => ({
                        status: status.value,
                        value: result,
                    })));
                }));
            }
        }
        util_js_1.util.assertNever(effect);
    }
}
exports.ZodEffects = ZodEffects;
exports.ZodTransformer = ZodEffects;
ZodEffects.create = (/**
 * @template I
 * @param {?} schema
 * @param {({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?})} effect
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodEffects<?, ?, ?>}
 */
(schema, effect, params) => {
    return new ZodEffects({
        schema,
        typeName: ZodFirstPartyTypeKind.ZodEffects,
        effect,
        ...processCreateParams(params),
    });
});
ZodEffects.createWithPreprocess = (/**
 * @template I
 * @param {function(*, !RefinementCtx): *} preprocess
 * @param {?} schema
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodEffects<?, ?, *>}
 */
(preprocess, schema, params) => {
    return new ZodEffects({
        schema,
        effect: { type: "preprocess", transform: preprocess },
        typeName: ZodFirstPartyTypeKind.ZodEffects,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, ({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?}), (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEffects<?, ?, ?>}
     * @public
     */
    ZodEffects.create;
    /**
     * @type {function(function(*, !RefinementCtx): *, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEffects<?, ?, *>}
     * @public
     */
    ZodEffects.createWithPreprocess;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodOptionalDef() { }
exports.ZodOptionalDef = ZodOptionalDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodOptionalDef.prototype.innerType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodOptionalDef.prototype.typeName;
}
/** @typedef {!ZodOptional<?>} */
exports.ZodOptionalType;
/**
 * @template T
 * @extends {ZodType<(undefined|?), !ZodOptionalDef, (undefined|?)>}
 */
class ZodOptional extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType === util_js_1.ZodParsedType.undefined) {
            return (0, parseUtil_js_1.OK)(undefined);
        }
        return this._def.innerType._parse(input);
    }
    /**
     * @public
     * @return {T}
     */
    unwrap() {
        return this._def.innerType;
    }
}
exports.ZodOptional = ZodOptional;
ZodOptional.create = (/**
 * @template Inner
 * @param {?} type
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodOptional<?>}
 */
(type, params) => {
    return (/** @type {?} */ (new ZodOptional({
        innerType: type,
        typeName: ZodFirstPartyTypeKind.ZodOptional,
        ...processCreateParams(params),
    })));
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodOptional<?>}
     * @public
     */
    ZodOptional.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodNullableDef() { }
exports.ZodNullableDef = ZodNullableDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodNullableDef.prototype.innerType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNullableDef.prototype.typeName;
}
/** @typedef {!ZodNullable<?>} */
exports.ZodNullableType;
/**
 * @template T
 * @extends {ZodType<(null|?), !ZodNullableDef, (null|?)>}
 */
class ZodNullable extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType === util_js_1.ZodParsedType.null) {
            return (0, parseUtil_js_1.OK)(null);
        }
        return this._def.innerType._parse(input);
    }
    /**
     * @public
     * @return {T}
     */
    unwrap() {
        return this._def.innerType;
    }
}
exports.ZodNullable = ZodNullable;
ZodNullable.create = (/**
 * @template Inner
 * @param {?} type
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodNullable<?>}
 */
(type, params) => {
    return (/** @type {?} */ (new ZodNullable({
        innerType: type,
        typeName: ZodFirstPartyTypeKind.ZodNullable,
        ...processCreateParams(params),
    })));
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNullable<?>}
     * @public
     */
    ZodNullable.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodDefaultDef() { }
exports.ZodDefaultDef = ZodDefaultDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodDefaultDef.prototype.innerType;
    /**
     * @type {function(): ?}
     * @public
     */
    ZodDefaultDef.prototype.defaultValue;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodDefaultDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<?, !ZodDefaultDef, (undefined|?)>}
 */
class ZodDefault extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        /** @type {?} */
        let data = ctx.data;
        if (ctx.parsedType === util_js_1.ZodParsedType.undefined) {
            data = this._def.defaultValue();
        }
        return this._def.innerType._parse({
            data,
            path: ctx.path,
            parent: ctx,
        });
    }
    /**
     * @public
     * @return {T}
     */
    removeDefault() {
        return this._def.innerType;
    }
}
exports.ZodDefault = ZodDefault;
ZodDefault.create = (/**
 * @template Inner
 * @param {?} type
 * @param {?} params
 * @return {!ZodDefault<?>}
 */
(type, params) => {
    return (/** @type {?} */ (new ZodDefault({
        innerType: type,
        typeName: ZodFirstPartyTypeKind.ZodDefault,
        defaultValue: typeof params.default === "function" ? params.default : (/**
         * @return {?}
         */
        () => (/** @type {?} */ (params.default))),
        ...processCreateParams(params),
    })));
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, ?): !ZodDefault<?>}
     * @public
     */
    ZodDefault.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodCatchDef() { }
exports.ZodCatchDef = ZodCatchDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodCatchDef.prototype.innerType;
    /**
     * @type {function({error: !tsickle_ZodError_1.ZodError<?>, input: *}): ?}
     * @public
     */
    ZodCatchDef.prototype.catchValue;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodCatchDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<?, !ZodCatchDef, *>}
 */
class ZodCatch extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        // newCtx is used to not collect issues from inner types in ctx
        /** @type {!tsickle_parseUtil_5.ParseContext} */
        const newCtx = {
            ...ctx,
            common: {
                ...ctx.common,
                issues: [],
            },
        };
        /** @type {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} */
        const result = this._def.innerType._parse({
            data: newCtx.data,
            path: newCtx.path,
            parent: {
                ...newCtx,
            },
        });
        if ((0, parseUtil_js_1.isAsync)(result)) {
            return (/** @type {!Promise<({status: string, value: ?}|{status: string})>} */ (result)).then((/**
             * @param {({status: string, value: ?}|{status: string})} result
             * @return {{status: string, value: ?}}
             */
            (result) => {
                return {
                    status: "valid",
                    value: result.status === "valid"
                        ? (/** @type {{status: string, value: ?}} */ (result)).value
                        : this._def.catchValue({
                            /**
                             * @public
                             * @return {!tsickle_ZodError_1.ZodError<?>}
                             */
                            get error() {
                                return new ZodError_js_1.ZodError(newCtx.common.issues);
                            },
                            input: newCtx.data,
                        }),
                };
            }));
        }
        else {
            return {
                status: "valid",
                value: (/** @type {({status: string, value: ?}|{status: string})} */ (result)).status === "valid"
                    ? (/** @type {{status: string, value: ?}} */ (result)).value
                    : this._def.catchValue({
                        /**
                         * @public
                         * @return {!tsickle_ZodError_1.ZodError<?>}
                         */
                        get error() {
                            return new ZodError_js_1.ZodError(newCtx.common.issues);
                        },
                        input: newCtx.data,
                    }),
            };
        }
    }
    /**
     * @public
     * @return {T}
     */
    removeCatch() {
        return this._def.innerType;
    }
}
exports.ZodCatch = ZodCatch;
ZodCatch.create = (/**
 * @template Inner
 * @param {?} type
 * @param {?} params
 * @return {!ZodCatch<?>}
 */
(type, params) => {
    return new ZodCatch({
        innerType: type,
        typeName: ZodFirstPartyTypeKind.ZodCatch,
        catchValue: typeof params.catch === "function" ? params.catch : (/**
         * @return {(function(): ?|?)}
         */
        () => params.catch),
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, ?): !ZodCatch<?>}
     * @public
     */
    ZodCatch.create;
}
/**
 * @record
 * @extends {ZodTypeDef}
 */
function ZodNaNDef() { }
exports.ZodNaNDef = ZodNaNDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodNaNDef.prototype.typeName;
}
/**
 * @extends {ZodType<number, !ZodNaNDef, number>}
 */
class ZodNaN extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {string} */
        const parsedType = this._getType(input);
        if (parsedType !== util_js_1.ZodParsedType.nan) {
            /** @type {!tsickle_parseUtil_5.ParseContext} */
            const ctx = this._getOrReturnCtx(input);
            (0, parseUtil_js_1.addIssueToContext)(ctx, {
                code: ZodError_js_1.ZodIssueCode.invalid_type,
                expected: util_js_1.ZodParsedType.nan,
                received: ctx.parsedType,
            });
            return parseUtil_js_1.INVALID;
        }
        return { status: "valid", value: input.data };
    }
}
exports.ZodNaN = ZodNaN;
ZodNaN.create = (/**
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodNaN}
 */
(params) => {
    return new ZodNaN({
        typeName: ZodFirstPartyTypeKind.ZodNaN,
        ...processCreateParams(params),
    });
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNaN}
     * @public
     */
    ZodNaN.create;
}
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodBrandedDef() { }
exports.ZodBrandedDef = ZodBrandedDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodBrandedDef.prototype.type;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodBrandedDef.prototype.typeName;
}
/** @type {symbol} */
exports.BRAND = Symbol("zod_brand");
/**
 * @template T, B
 * @extends {ZodType<?, !ZodBrandedDef, ?>}
 */
class ZodBranded extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { ctx } = this._processInputParams(input);
        /** @type {?} */
        const data = ctx.data;
        return this._def.type._parse({
            data,
            path: ctx.path,
            parent: ctx,
        });
    }
    /**
     * @public
     * @return {T}
     */
    unwrap() {
        return this._def.type;
    }
}
exports.ZodBranded = ZodBranded;
/**
 * @record
 * @template A, B
 * @extends {ZodTypeDef}
 */
function ZodPipelineDef() { }
exports.ZodPipelineDef = ZodPipelineDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {A}
     * @public
     */
    ZodPipelineDef.prototype.in;
    /**
     * @type {B}
     * @public
     */
    ZodPipelineDef.prototype.out;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodPipelineDef.prototype.typeName;
}
/**
 * @template A, B
 * @extends {ZodType<?, !ZodPipelineDef<A>, ?>}
 */
class ZodPipeline extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        const { status, ctx } = this._processInputParams(input);
        if (ctx.common.async) {
            /** @type {function(): !Promise<({status: string, value: ?}|{status: string})>} */
            const handleAsync = (/**
             * @return {!Promise<({status: string, value: ?}|{status: string})>}
             */
            async () => {
                /** @type {({status: string, value: ?}|{status: string})} */
                const inResult = await this._def.in._parseAsync({
                    data: ctx.data,
                    path: ctx.path,
                    parent: ctx,
                });
                if (inResult.status === "aborted")
                    return parseUtil_js_1.INVALID;
                if ((/** @type {{status: string, value: ?}} */ (inResult)).status === "dirty") {
                    status.dirty();
                    return (0, parseUtil_js_1.DIRTY)((/** @type {{status: string, value: ?}} */ (inResult)).value);
                }
                else {
                    return this._def.out._parseAsync({
                        data: (/** @type {{status: string, value: ?}} */ (inResult)).value,
                        path: ctx.path,
                        parent: ctx,
                    });
                }
            });
            return handleAsync();
        }
        else {
            /** @type {({status: string, value: ?}|{status: string})} */
            const inResult = this._def.in._parseSync({
                data: ctx.data,
                path: ctx.path,
                parent: ctx,
            });
            if (inResult.status === "aborted")
                return parseUtil_js_1.INVALID;
            if ((/** @type {{status: string, value: ?}} */ (inResult)).status === "dirty") {
                status.dirty();
                return {
                    status: "dirty",
                    value: (/** @type {{status: string, value: ?}} */ (inResult)).value,
                };
            }
            else {
                return this._def.out._parseSync({
                    data: (/** @type {{status: string, value: ?}} */ (inResult)).value,
                    path: ctx.path,
                    parent: ctx,
                });
            }
        }
    }
    /**
     * @public
     * @template ASchema, BSchema
     * @param {ASchema} a
     * @param {BSchema} b
     * @return {!ZodPipeline<ASchema, BSchema>}
     */
    static create(a, b) {
        return new ZodPipeline({
            in: a,
            out: b,
            typeName: ZodFirstPartyTypeKind.ZodPipeline,
        });
    }
}
exports.ZodPipeline = ZodPipeline;
/** @typedef {(!Date|!Error|!Generator<*, ?, ?>|!Promise<*>|!RegExp|function(...?): ?|function(new:?, ...?)|*)} */
var BuiltIn;
/** @typedef {?} */
var MakeReadonly;
/**
 * @record
 * @template T
 * @extends {ZodTypeDef}
 */
function ZodReadonlyDef() { }
exports.ZodReadonlyDef = ZodReadonlyDef;
/* istanbul ignore if */
if (false) {
    /**
     * @type {T}
     * @public
     */
    ZodReadonlyDef.prototype.innerType;
    /**
     * @type {!ZodFirstPartyTypeKind}
     * @public
     */
    ZodReadonlyDef.prototype.typeName;
}
/**
 * @template T
 * @extends {ZodType<?, !ZodReadonlyDef, ?>}
 */
class ZodReadonly extends ZodType {
    /**
     * @public
     * @param {{data: ?, path: !Array<(string|number)>, parent: !tsickle_parseUtil_5.ParseContext}} input
     * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
     */
    _parse(input) {
        /** @type {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} */
        const result = this._def.innerType._parse(input);
        /** @type {function((!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})): (!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} */
        const freeze = (/**
         * @param {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})} data
         * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
         */
        (data) => {
            if ((0, parseUtil_js_1.isValid)(data)) {
                (/** @type {{status: string, value: ?}} */ (data)).value = Object.freeze((/** @type {{status: string, value: ?}} */ (data)).value);
            }
            return data;
        });
        return (0, parseUtil_js_1.isAsync)(result) ? (/** @type {!Promise<({status: string, value: ?}|{status: string})>} */ (result)).then((/**
         * @param {({status: string, value: ?}|{status: string})} data
         * @return {(!Promise<({status: string, value: ?}|{status: string})>|{status: string, value: ?}|{status: string})}
         */
        (data) => freeze(data))) : freeze(result);
    }
    /**
     * @public
     * @return {T}
     */
    unwrap() {
        return this._def.innerType;
    }
}
exports.ZodReadonly = ZodReadonly;
ZodReadonly.create = (/**
 * @template Inner
 * @param {?} type
 * @param {(undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=} params
 * @return {!ZodReadonly<?>}
 */
(type, params) => {
    return (/** @type {?} */ (new ZodReadonly({
        innerType: type,
        typeName: ZodFirstPartyTypeKind.ZodReadonly,
        ...processCreateParams(params),
    })));
});
/* istanbul ignore if */
if (false) {
    /**
     * @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodReadonly<?>}
     * @public
     */
    ZodReadonly.create;
}
////////////////////////////////////////
////////////////////////////////////////
//////////                    //////////
//////////      z.custom      //////////
//////////                    //////////
////////////////////////////////////////
////////////////////////////////////////
/**
 * @param {*} params
 * @param {*} data
 * @return {?}
 */
function cleanParams(params, data) {
    /** @type {?} */
    const p = typeof params === "function" ? params(data) : typeof params === "string" ? { message: params } : params;
    /** @type {?} */
    const p2 = typeof p === "string" ? { message: p } : p;
    return p2;
}
/** @typedef {?} */
var CustomParams;
/**
 * @template T
 * @param {(undefined|function(?): ?)=} check
 * @param {(string|function(?): ?|?)=} _params
 * @param {(undefined|boolean)=} fatal
 * @return {!ZodType<T, !ZodTypeDef, T>}
 */
function custom(check, _params = {}, 
/**
 * @deprecated
 *
 * Pass `fatal` into the params object instead:
 *
 * ```ts
 * z.string().custom((val) => val.length > 5, { fatal: false })
 * ```
 *
 */
fatal) {
    if (check)
        return ZodAny.create().superRefine((/**
         * @param {?} data
         * @param {!RefinementCtx} ctx
         * @return {(undefined|!Promise<void>)}
         */
        (data, ctx) => {
            /** @type {?} */
            const r = check(data);
            if (r instanceof Promise) {
                return (/** @type {!Promise<?>} */ (r)).then((/**
                 * @param {?} r
                 * @return {void}
                 */
                (r) => {
                    if (!r) {
                        /** @type {?} */
                        const params = cleanParams(_params, data);
                        /** @type {?} */
                        const _fatal = params.fatal ?? fatal ?? true;
                        ctx.addIssue({ code: "custom", ...params, fatal: _fatal });
                    }
                }));
            }
            if (!r) {
                /** @type {?} */
                const params = cleanParams(_params, data);
                /** @type {?} */
                const _fatal = params.fatal ?? fatal ?? true;
                ctx.addIssue({ code: "custom", ...params, fatal: _fatal });
            }
            return;
        }));
    return ZodAny.create();
}
exports.custom = custom;
/** @type {{object: function(function(): ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>}} */
exports.late = {
    object: ZodObject.lazycreate,
};
/** @enum {string} */
var ZodFirstPartyTypeKind = {
    ZodString: "ZodString",
    ZodNumber: "ZodNumber",
    ZodNaN: "ZodNaN",
    ZodBigInt: "ZodBigInt",
    ZodBoolean: "ZodBoolean",
    ZodDate: "ZodDate",
    ZodSymbol: "ZodSymbol",
    ZodUndefined: "ZodUndefined",
    ZodNull: "ZodNull",
    ZodAny: "ZodAny",
    ZodUnknown: "ZodUnknown",
    ZodNever: "ZodNever",
    ZodVoid: "ZodVoid",
    ZodArray: "ZodArray",
    ZodObject: "ZodObject",
    ZodUnion: "ZodUnion",
    ZodDiscriminatedUnion: "ZodDiscriminatedUnion",
    ZodIntersection: "ZodIntersection",
    ZodTuple: "ZodTuple",
    ZodRecord: "ZodRecord",
    ZodMap: "ZodMap",
    ZodSet: "ZodSet",
    ZodFunction: "ZodFunction",
    ZodLazy: "ZodLazy",
    ZodLiteral: "ZodLiteral",
    ZodEnum: "ZodEnum",
    ZodEffects: "ZodEffects",
    ZodNativeEnum: "ZodNativeEnum",
    ZodOptional: "ZodOptional",
    ZodNullable: "ZodNullable",
    ZodDefault: "ZodDefault",
    ZodCatch: "ZodCatch",
    ZodPromise: "ZodPromise",
    ZodBranded: "ZodBranded",
    ZodPipeline: "ZodPipeline",
    ZodReadonly: "ZodReadonly",
};
exports.ZodFirstPartyTypeKind = ZodFirstPartyTypeKind;
/** @typedef {(!ZodAny|!ZodArray<?, ?>|!ZodBigInt|!ZodBoolean|!ZodBranded<?, ?>|!ZodCatch<?>|!ZodDate|!ZodDefault<?>|!ZodDiscriminatedUnion<?, ?>|!ZodEffects<?, ?, ?>|!ZodEnum<?>|!ZodFunction<?, ?>|!ZodIntersection<?, ?>|!ZodLazy<?>|!ZodLiteral<?>|!ZodMap<?, !ZodType<?, ?, ?>>|!ZodNaN|!ZodNativeEnum<?>|!ZodNever|!ZodNull|!ZodNullable<?>|!ZodNumber|!ZodObject<?, ?, ?, ?, ?>|!ZodOptional<?>|!ZodPipeline<?, ?>|!ZodPromise<?>|!ZodReadonly<?>|!ZodRecord<?, ?>|!ZodSet<?>|!ZodString|!ZodSymbol|!ZodTuple<?, ?>|!ZodUndefined|!ZodUnion<?>|!ZodUnknown|!ZodVoid)} */
exports.ZodFirstPartySchemaTypes;
// requires TS 4.4+
/**
 * @abstract
 */
class Class {
    /**
     * @public
     * @param {...?} _
     */
    constructor(..._) { }
}
/** @type {function(?, ?=): !ZodType<?, !ZodTypeDef, ?>} */
const instanceOfType = (/**
 * @template T
 * @param {?} cls
 * @param {?=} params
 * @return {!ZodType<?, !ZodTypeDef, ?>}
 */
(
// const instanceOfType = <T extends new (...args: any[]) => any>(
cls, params = {
    message: `Input not instance of ${cls.name}`,
}) => custom((/**
 * @param {?} data
 * @return {boolean}
 */
(data) => data instanceof cls), params));
exports.instanceof = instanceOfType;
/** @type {function((undefined|?)=): !ZodString} */
const stringType = ZodString.create;
exports.string = stringType;
/** @type {function((undefined|?)=): !ZodNumber} */
const numberType = ZodNumber.create;
exports.number = numberType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNaN} */
const nanType = ZodNaN.create;
exports.nan = nanType;
/** @type {function((undefined|?)=): !ZodBigInt} */
const bigIntType = ZodBigInt.create;
exports.bigint = bigIntType;
/** @type {function((undefined|?)=): !ZodBoolean} */
const booleanType = ZodBoolean.create;
exports.boolean = booleanType;
/** @type {function((undefined|?)=): !ZodDate} */
const dateType = ZodDate.create;
exports.date = dateType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodSymbol} */
const symbolType = ZodSymbol.create;
exports.symbol = symbolType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUndefined} */
const undefinedType = ZodUndefined.create;
exports.undefined = undefinedType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNull} */
const nullType = ZodNull.create;
exports.null = nullType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodAny} */
const anyType = ZodAny.create;
exports.any = anyType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUnknown} */
const unknownType = ZodUnknown.create;
exports.unknown = unknownType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNever} */
const neverType = ZodNever.create;
exports.never = neverType;
/** @type {function((undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodVoid} */
const voidType = ZodVoid.create;
exports.void = voidType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodArray<?, string>} */
const arrayType = ZodArray.create;
exports.array = arrayType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>} */
const objectType = ZodObject.create;
exports.object = objectType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodObject<?, string, !ZodType<?, ?, ?>, ?, ?>} */
const strictObjectType = ZodObject.strictCreate;
exports.strictObject = strictObjectType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodUnion<?>} */
const unionType = ZodUnion.create;
exports.union = unionType;
/** @type {function(Discriminator, Types, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodDiscriminatedUnion<Discriminator, Types>} */
const discriminatedUnionType = ZodDiscriminatedUnion.create;
exports.discriminatedUnion = discriminatedUnionType;
/** @type {function(?, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodIntersection<?, ?>} */
const intersectionType = ZodIntersection.create;
exports.intersection = intersectionType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodTuple<?, null>} */
const tupleType = ZodTuple.create;
exports.tuple = tupleType;
/** @type {function(?, ?=, ?=): !ZodRecord<?, ?>} */
const recordType = ZodRecord.create;
exports.record = recordType;
/** @type {function(?, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodMap<?, ?>} */
const mapType = ZodMap.create;
exports.map = mapType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodSet<?>} */
const setType = ZodSet.create;
exports.set = setType;
/** @type {function((undefined|!ZodTuple<!Array<?>, (null|!ZodType<?, ?, ?>)>)=, (undefined|!ZodType<?, ?, ?>)=, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): ?} */
const functionType = ZodFunction.create;
exports.function = functionType;
/** @type {function(function(): ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodLazy<?>} */
const lazyType = ZodLazy.create;
exports.lazy = lazyType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodLiteral<?>} */
const literalType = ZodLiteral.create;
exports.literal = literalType;
/** @type {function(!Array<?>, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEnum<!Array<?>>} */
const enumType = ZodEnum.create;
exports.enum = enumType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNativeEnum<?>} */
const nativeEnumType = ZodNativeEnum.create;
exports.nativeEnum = nativeEnumType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodPromise<?>} */
const promiseType = ZodPromise.create;
exports.promise = promiseType;
/** @type {function(?, ({type: string, transform: function(?, !RefinementCtx): ?}|{type: string, refinement: function(?, !RefinementCtx): ?}), (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEffects<?, ?, ?>} */
const effectsType = ZodEffects.create;
exports.effect = effectsType;
exports.transformer = effectsType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodOptional<?>} */
const optionalType = ZodOptional.create;
exports.optional = optionalType;
/** @type {function(?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodNullable<?>} */
const nullableType = ZodNullable.create;
exports.nullable = nullableType;
/** @type {function(function(*, !RefinementCtx): *, ?, (undefined|{errorMap: (undefined|function((!tsickle_ZodError_1.ZodCustomIssue|!tsickle_ZodError_1.ZodInvalidArgumentsIssue|!tsickle_ZodError_1.ZodInvalidDateIssue|!tsickle_ZodError_1.ZodInvalidEnumValueIssue|!tsickle_ZodError_1.ZodInvalidIntersectionTypesIssue|!tsickle_ZodError_1.ZodInvalidLiteralIssue|!tsickle_ZodError_1.ZodInvalidReturnTypeIssue|!tsickle_ZodError_1.ZodInvalidStringIssue|!tsickle_ZodError_1.ZodInvalidTypeIssue|!tsickle_ZodError_1.ZodInvalidUnionDiscriminatorIssue|!tsickle_ZodError_1.ZodInvalidUnionIssue|!tsickle_ZodError_1.ZodNotFiniteIssue|!tsickle_ZodError_1.ZodNotMultipleOfIssue|!tsickle_ZodError_1.ZodTooBigIssue|!tsickle_ZodError_1.ZodTooSmallIssue|!tsickle_ZodError_1.ZodUnrecognizedKeysIssue), {defaultError: string, data: ?}): {message: string}), invalid_type_error: (undefined|string), required_error: (undefined|string), message: (undefined|string), description: (undefined|string)})=): !ZodEffects<?, ?, *>} */
const preprocessType = ZodEffects.createWithPreprocess;
exports.preprocess = preprocessType;
/** @type {function(ASchema, BSchema): !ZodPipeline<ASchema, BSchema>} */
const pipelineType = ZodPipeline.create;
exports.pipeline = pipelineType;
/** @type {function(): !ZodOptional<!ZodString>} */
const ostring = (/**
 * @return {!ZodOptional<!ZodString>}
 */
() => stringType().optional());
exports.ostring = ostring;
/** @type {function(): !ZodOptional<!ZodNumber>} */
const onumber = (/**
 * @return {!ZodOptional<!ZodNumber>}
 */
() => numberType().optional());
exports.onumber = onumber;
/** @type {function(): !ZodOptional<!ZodBoolean>} */
const oboolean = (/**
 * @return {!ZodOptional<!ZodBoolean>}
 */
() => booleanType().optional());
exports.oboolean = oboolean;
/** @type {{string: function((undefined|?)=): !ZodString, number: function((undefined|?)=): !ZodNumber, boolean: function((undefined|?)=): !ZodBoolean, bigint: function((undefined|?)=): !ZodBigInt, date: function((undefined|?)=): !ZodDate}} */
exports.coerce = {
    string: (/** @type {function((undefined|?)=): !ZodString} */ (((/**
     * @param {(undefined|?)} arg
     * @return {!ZodString}
     */
    (arg) => ZodString.create({ ...arg, coerce: true }))))),
    number: (/** @type {function((undefined|?)=): !ZodNumber} */ (((/**
     * @param {(undefined|?)} arg
     * @return {!ZodNumber}
     */
    (arg) => ZodNumber.create({ ...arg, coerce: true }))))),
    boolean: (/** @type {function((undefined|?)=): !ZodBoolean} */ (((/**
     * @param {(undefined|?)} arg
     * @return {!ZodBoolean}
     */
    (arg) => ZodBoolean.create({
        ...arg,
        coerce: true,
    }))))),
    bigint: (/** @type {function((undefined|?)=): !ZodBigInt} */ (((/**
     * @param {(undefined|?)} arg
     * @return {!ZodBigInt}
     */
    (arg) => ZodBigInt.create({ ...arg, coerce: true }))))),
    date: (/** @type {function((undefined|?)=): !ZodDate} */ (((/**
     * @param {(undefined|?)} arg
     * @return {!ZodDate}
     */
    (arg) => ZodDate.create({ ...arg, coerce: true }))))),
};
/** @type {?} */
exports.NEVER = (/** @type {?} */ (parseUtil_js_1.INVALID));

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/v3/external.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.external');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/v3/external.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_errors_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors");
const tsickle_parseUtil_2 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.parseUtil");
const tsickle_typeAliases_3 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.typeAliases");
const tsickle_util_4 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util");
const tsickle_types_5 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.types");
const tsickle_ZodError_6 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError");
const errors_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.errors');
exports.setErrorMap = errors_js_1.setErrorMap;
exports.getErrorMap = errors_js_1.getErrorMap;
exports.defaultErrorMap = errors_js_1.defaultErrorMap;
const parseUtil_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.parseUtil');
exports.addIssueToContext = parseUtil_js_1.addIssueToContext;
exports.makeIssue = parseUtil_js_1.makeIssue;
exports.EMPTY_PATH = parseUtil_js_1.EMPTY_PATH;
exports.ParseStatus = parseUtil_js_1.ParseStatus;
exports.INVALID = parseUtil_js_1.INVALID;
exports.DIRTY = parseUtil_js_1.DIRTY;
exports.OK = parseUtil_js_1.OK;
exports.isAborted = parseUtil_js_1.isAborted;
exports.isDirty = parseUtil_js_1.isDirty;
exports.isValid = parseUtil_js_1.isValid;
exports.isAsync = parseUtil_js_1.isAsync;
/** @typedef {!tsickle_parseUtil_2.ParseParams} */
exports.ParseParams; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParsePathComponent} */
exports.ParsePathComponent; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParsePath} */
exports.ParsePath; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParseContext} */
exports.ParseContext; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParseInput} */
exports.ParseInput; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ObjectPair} */
exports.ObjectPair; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParseResult} */
exports.ParseResult; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.SyncParseReturnType} */
exports.SyncParseReturnType; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.AsyncParseReturnType} */
exports.AsyncParseReturnType; // re-export typedef
/** @typedef {!tsickle_parseUtil_2.ParseReturnType} */
exports.ParseReturnType; // re-export typedef
const typeAliases_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.typeAliases');
/** @typedef {!tsickle_typeAliases_3.Primitive} */
exports.Primitive; // re-export typedef
/** @typedef {!tsickle_typeAliases_3.Scalars} */
exports.Scalars; // re-export typedef
const util_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.helpers.util');
exports.util = util_js_1.util;
exports.objectUtil = util_js_1.objectUtil;
exports.ZodParsedType = util_js_1.ZodParsedType;
exports.getParsedType = util_js_1.getParsedType;
const types_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.types');
exports.datetimeRegex = types_js_1.datetimeRegex;
exports.custom = types_js_1.custom;
exports.ZodType = types_js_1.ZodType;
exports.ZodString = types_js_1.ZodString;
exports.ZodNumber = types_js_1.ZodNumber;
exports.ZodBigInt = types_js_1.ZodBigInt;
exports.ZodBoolean = types_js_1.ZodBoolean;
exports.ZodDate = types_js_1.ZodDate;
exports.ZodSymbol = types_js_1.ZodSymbol;
exports.ZodUndefined = types_js_1.ZodUndefined;
exports.ZodNull = types_js_1.ZodNull;
exports.ZodAny = types_js_1.ZodAny;
exports.ZodUnknown = types_js_1.ZodUnknown;
exports.ZodNever = types_js_1.ZodNever;
exports.ZodVoid = types_js_1.ZodVoid;
exports.ZodArray = types_js_1.ZodArray;
exports.ZodObject = types_js_1.ZodObject;
exports.ZodUnion = types_js_1.ZodUnion;
exports.ZodDiscriminatedUnion = types_js_1.ZodDiscriminatedUnion;
exports.ZodIntersection = types_js_1.ZodIntersection;
exports.ZodTuple = types_js_1.ZodTuple;
exports.ZodRecord = types_js_1.ZodRecord;
exports.ZodMap = types_js_1.ZodMap;
exports.ZodSet = types_js_1.ZodSet;
exports.ZodFunction = types_js_1.ZodFunction;
exports.ZodLazy = types_js_1.ZodLazy;
exports.ZodLiteral = types_js_1.ZodLiteral;
exports.ZodEnum = types_js_1.ZodEnum;
exports.ZodNativeEnum = types_js_1.ZodNativeEnum;
exports.ZodPromise = types_js_1.ZodPromise;
exports.ZodEffects = types_js_1.ZodEffects;
exports.ZodTransformer = types_js_1.ZodTransformer;
exports.ZodOptional = types_js_1.ZodOptional;
exports.ZodNullable = types_js_1.ZodNullable;
exports.ZodDefault = types_js_1.ZodDefault;
exports.ZodCatch = types_js_1.ZodCatch;
exports.ZodNaN = types_js_1.ZodNaN;
exports.BRAND = types_js_1.BRAND;
exports.ZodBranded = types_js_1.ZodBranded;
exports.ZodPipeline = types_js_1.ZodPipeline;
exports.ZodReadonly = types_js_1.ZodReadonly;
exports.Schema = types_js_1.Schema;
exports.ZodSchema = types_js_1.ZodSchema;
exports.late = types_js_1.late;
exports.ZodFirstPartyTypeKind = types_js_1.ZodFirstPartyTypeKind;
exports.coerce = types_js_1.coerce;
exports.any = types_js_1.any;
exports.array = types_js_1.array;
exports.bigint = types_js_1.bigint;
exports.boolean = types_js_1.boolean;
exports.date = types_js_1.date;
exports.discriminatedUnion = types_js_1.discriminatedUnion;
exports.effect = types_js_1.effect;
exports.enum = types_js_1.enum;
exports.function = types_js_1.function;
exports.instanceof = types_js_1.instanceof;
exports.intersection = types_js_1.intersection;
exports.lazy = types_js_1.lazy;
exports.literal = types_js_1.literal;
exports.map = types_js_1.map;
exports.nan = types_js_1.nan;
exports.nativeEnum = types_js_1.nativeEnum;
exports.never = types_js_1.never;
exports.null = types_js_1.null;
exports.nullable = types_js_1.nullable;
exports.number = types_js_1.number;
exports.object = types_js_1.object;
exports.oboolean = types_js_1.oboolean;
exports.onumber = types_js_1.onumber;
exports.optional = types_js_1.optional;
exports.ostring = types_js_1.ostring;
exports.pipeline = types_js_1.pipeline;
exports.preprocess = types_js_1.preprocess;
exports.promise = types_js_1.promise;
exports.record = types_js_1.record;
exports.set = types_js_1.set;
exports.strictObject = types_js_1.strictObject;
exports.string = types_js_1.string;
exports.symbol = types_js_1.symbol;
exports.transformer = types_js_1.transformer;
exports.tuple = types_js_1.tuple;
exports.undefined = types_js_1.undefined;
exports.union = types_js_1.union;
exports.unknown = types_js_1.unknown;
exports.void = types_js_1.void;
exports.NEVER = types_js_1.NEVER;
/** @typedef {!tsickle_types_5.RefinementCtx} */
exports.RefinementCtx; // re-export typedef
/** @typedef {!tsickle_types_5.ZodRawShape} */
exports.ZodRawShape; // re-export typedef
/** @typedef {!tsickle_types_5.ZodTypeAny} */
exports.ZodTypeAny; // re-export typedef
/** @typedef {!tsickle_types_5.infer} */
exports.TypeOf; // re-export typedef
/** @typedef {!tsickle_types_5.input} */
exports.input; // re-export typedef
/** @typedef {!tsickle_types_5.output} */
exports.output; // re-export typedef
/** @typedef {!tsickle_types_5.infer} */
exports.infer; // re-export typedef
/** @typedef {!tsickle_types_5.CustomErrorParams} */
exports.CustomErrorParams; // re-export typedef
/** @typedef {!tsickle_types_5.ZodTypeDef} */
exports.ZodTypeDef; // re-export typedef
/** @typedef {!tsickle_types_5.RawCreateParams} */
exports.RawCreateParams; // re-export typedef
/** @typedef {!tsickle_types_5.ProcessedCreateParams} */
exports.ProcessedCreateParams; // re-export typedef
/** @typedef {!tsickle_types_5.SafeParseSuccess} */
exports.SafeParseSuccess; // re-export typedef
/** @typedef {!tsickle_types_5.SafeParseError} */
exports.SafeParseError; // re-export typedef
/** @typedef {!tsickle_types_5.SafeParseReturnType} */
exports.SafeParseReturnType; // re-export typedef
/** @typedef {!tsickle_types_5.IpVersion} */
exports.IpVersion; // re-export typedef
/** @typedef {!tsickle_types_5.ZodStringCheck} */
exports.ZodStringCheck; // re-export typedef
/** @typedef {!tsickle_types_5.ZodStringDef} */
exports.ZodStringDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNumberCheck} */
exports.ZodNumberCheck; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNumberDef} */
exports.ZodNumberDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodBigIntCheck} */
exports.ZodBigIntCheck; // re-export typedef
/** @typedef {!tsickle_types_5.ZodBigIntDef} */
exports.ZodBigIntDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodBooleanDef} */
exports.ZodBooleanDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodDateCheck} */
exports.ZodDateCheck; // re-export typedef
/** @typedef {!tsickle_types_5.ZodDateDef} */
exports.ZodDateDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodSymbolDef} */
exports.ZodSymbolDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodUndefinedDef} */
exports.ZodUndefinedDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNullDef} */
exports.ZodNullDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodAnyDef} */
exports.ZodAnyDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodUnknownDef} */
exports.ZodUnknownDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNeverDef} */
exports.ZodNeverDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodVoidDef} */
exports.ZodVoidDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodArrayDef} */
exports.ZodArrayDef; // re-export typedef
/** @typedef {!tsickle_types_5.ArrayCardinality} */
exports.ArrayCardinality; // re-export typedef
/** @typedef {!tsickle_types_5.arrayOutputType} */
exports.arrayOutputType; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNonEmptyArray} */
exports.ZodNonEmptyArray; // re-export typedef
/** @typedef {!tsickle_types_5.UnknownKeysParam} */
exports.UnknownKeysParam; // re-export typedef
/** @typedef {!tsickle_types_5.ZodObjectDef} */
exports.ZodObjectDef; // re-export typedef
/** @typedef {!tsickle_types_5.mergeTypes} */
exports.mergeTypes; // re-export typedef
/** @typedef {!tsickle_types_5.objectOutputType} */
exports.objectOutputType; // re-export typedef
/** @typedef {!tsickle_types_5.baseObjectOutputType} */
exports.baseObjectOutputType; // re-export typedef
/** @typedef {!tsickle_types_5.objectInputType} */
exports.objectInputType; // re-export typedef
/** @typedef {!tsickle_types_5.baseObjectInputType} */
exports.baseObjectInputType; // re-export typedef
/** @typedef {!tsickle_types_5.CatchallOutput} */
exports.CatchallOutput; // re-export typedef
/** @typedef {!tsickle_types_5.CatchallInput} */
exports.CatchallInput; // re-export typedef
/** @typedef {!tsickle_types_5.PassthroughType} */
exports.PassthroughType; // re-export typedef
/** @typedef {!tsickle_types_5.deoptional} */
exports.deoptional; // re-export typedef
/** @typedef {!tsickle_types_5.SomeZodObject} */
exports.SomeZodObject; // re-export typedef
/** @typedef {!tsickle_types_5.noUnrecognized} */
exports.noUnrecognized; // re-export typedef
/** @typedef {!tsickle_types_5.AnyZodObject} */
exports.AnyZodObject; // re-export typedef
/** @typedef {!tsickle_types_5.ZodUnionOptions} */
exports.ZodUnionOptions; // re-export typedef
/** @typedef {!tsickle_types_5.ZodUnionDef} */
exports.ZodUnionDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodDiscriminatedUnionOption} */
exports.ZodDiscriminatedUnionOption; // re-export typedef
/** @typedef {!tsickle_types_5.ZodDiscriminatedUnionDef} */
exports.ZodDiscriminatedUnionDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodIntersectionDef} */
exports.ZodIntersectionDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodTupleItems} */
exports.ZodTupleItems; // re-export typedef
/** @typedef {!tsickle_types_5.AssertArray} */
exports.AssertArray; // re-export typedef
/** @typedef {!tsickle_types_5.OutputTypeOfTuple} */
exports.OutputTypeOfTuple; // re-export typedef
/** @typedef {!tsickle_types_5.OutputTypeOfTupleWithRest} */
exports.OutputTypeOfTupleWithRest; // re-export typedef
/** @typedef {!tsickle_types_5.InputTypeOfTuple} */
exports.InputTypeOfTuple; // re-export typedef
/** @typedef {!tsickle_types_5.InputTypeOfTupleWithRest} */
exports.InputTypeOfTupleWithRest; // re-export typedef
/** @typedef {!tsickle_types_5.ZodTupleDef} */
exports.ZodTupleDef; // re-export typedef
/** @typedef {!tsickle_types_5.AnyZodTuple} */
exports.AnyZodTuple; // re-export typedef
/** @typedef {!tsickle_types_5.ZodRecordDef} */
exports.ZodRecordDef; // re-export typedef
/** @typedef {!tsickle_types_5.KeySchema} */
exports.KeySchema; // re-export typedef
/** @typedef {!tsickle_types_5.RecordType} */
exports.RecordType; // re-export typedef
/** @typedef {!tsickle_types_5.ZodMapDef} */
exports.ZodMapDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodSetDef} */
exports.ZodSetDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodFunctionDef} */
exports.ZodFunctionDef; // re-export typedef
/** @typedef {!tsickle_types_5.OuterTypeOfFunction} */
exports.OuterTypeOfFunction; // re-export typedef
/** @typedef {!tsickle_types_5.InnerTypeOfFunction} */
exports.InnerTypeOfFunction; // re-export typedef
/** @typedef {!tsickle_types_5.ZodLazyDef} */
exports.ZodLazyDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodLiteralDef} */
exports.ZodLiteralDef; // re-export typedef
/** @typedef {!tsickle_types_5.ArrayKeys} */
exports.ArrayKeys; // re-export typedef
/** @typedef {!tsickle_types_5.Indices} */
exports.Indices; // re-export typedef
/** @typedef {!tsickle_types_5.EnumValues} */
exports.EnumValues; // re-export typedef
/** @typedef {!tsickle_types_5.Values} */
exports.Values; // re-export typedef
/** @typedef {!tsickle_types_5.ZodEnumDef} */
exports.ZodEnumDef; // re-export typedef
/** @typedef {!tsickle_types_5.Writeable} */
exports.Writeable; // re-export typedef
/** @typedef {!tsickle_types_5.FilterEnum} */
exports.FilterEnum; // re-export typedef
/** @typedef {!tsickle_types_5.typecast} */
exports.typecast; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNativeEnumDef} */
exports.ZodNativeEnumDef; // re-export typedef
/** @typedef {!tsickle_types_5.EnumLike} */
exports.EnumLike; // re-export typedef
/** @typedef {!tsickle_types_5.ZodPromiseDef} */
exports.ZodPromiseDef; // re-export typedef
/** @typedef {!tsickle_types_5.Refinement} */
exports.Refinement; // re-export typedef
/** @typedef {!tsickle_types_5.SuperRefinement} */
exports.SuperRefinement; // re-export typedef
/** @typedef {!tsickle_types_5.RefinementEffect} */
exports.RefinementEffect; // re-export typedef
/** @typedef {!tsickle_types_5.TransformEffect} */
exports.TransformEffect; // re-export typedef
/** @typedef {!tsickle_types_5.PreprocessEffect} */
exports.PreprocessEffect; // re-export typedef
/** @typedef {!tsickle_types_5.Effect} */
exports.Effect; // re-export typedef
/** @typedef {!tsickle_types_5.ZodEffectsDef} */
exports.ZodEffectsDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodOptionalDef} */
exports.ZodOptionalDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodOptionalType} */
exports.ZodOptionalType; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNullableDef} */
exports.ZodNullableDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNullableType} */
exports.ZodNullableType; // re-export typedef
/** @typedef {!tsickle_types_5.ZodDefaultDef} */
exports.ZodDefaultDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodCatchDef} */
exports.ZodCatchDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodNaNDef} */
exports.ZodNaNDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodBrandedDef} */
exports.ZodBrandedDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodPipelineDef} */
exports.ZodPipelineDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodReadonlyDef} */
exports.ZodReadonlyDef; // re-export typedef
/** @typedef {!tsickle_types_5.ZodFirstPartySchemaTypes} */
exports.ZodFirstPartySchemaTypes; // re-export typedef
const ZodError_js_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.ZodError');
exports.ZodIssueCode = ZodError_js_1.ZodIssueCode;
exports.quotelessJson = ZodError_js_1.quotelessJson;
exports.ZodError = ZodError_js_1.ZodError;
/** @typedef {!tsickle_ZodError_6.inferFlattenedErrors} */
exports.inferFlattenedErrors; // re-export typedef
/** @typedef {!tsickle_ZodError_6.typeToFlattenedError} */
exports.typeToFlattenedError; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodIssueBase} */
exports.ZodIssueBase; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidTypeIssue} */
exports.ZodInvalidTypeIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidLiteralIssue} */
exports.ZodInvalidLiteralIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodUnrecognizedKeysIssue} */
exports.ZodUnrecognizedKeysIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidUnionIssue} */
exports.ZodInvalidUnionIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidUnionDiscriminatorIssue} */
exports.ZodInvalidUnionDiscriminatorIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidEnumValueIssue} */
exports.ZodInvalidEnumValueIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidArgumentsIssue} */
exports.ZodInvalidArgumentsIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidReturnTypeIssue} */
exports.ZodInvalidReturnTypeIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidDateIssue} */
exports.ZodInvalidDateIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.StringValidation} */
exports.StringValidation; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidStringIssue} */
exports.ZodInvalidStringIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodTooSmallIssue} */
exports.ZodTooSmallIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodTooBigIssue} */
exports.ZodTooBigIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodInvalidIntersectionTypesIssue} */
exports.ZodInvalidIntersectionTypesIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodNotMultipleOfIssue} */
exports.ZodNotMultipleOfIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodNotFiniteIssue} */
exports.ZodNotFiniteIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodCustomIssue} */
exports.ZodCustomIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.DenormalizedError} */
exports.DenormalizedError; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodIssueOptionalMessage} */
exports.ZodIssueOptionalMessage; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodIssue} */
exports.ZodIssue; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodFormattedError} */
exports.ZodFormattedError; // re-export typedef
/** @typedef {!tsickle_ZodError_6.inferFormattedError} */
exports.inferFormattedError; // re-export typedef
/** @typedef {!tsickle_ZodError_6.IssueData} */
exports.IssueData; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ErrorMapCtx} */
exports.ErrorMapCtx; // re-export typedef
/** @typedef {!tsickle_ZodError_6.ZodErrorMap} */
exports.ZodErrorMap; // re-export typedef

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2025 Colin McDonnell
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/colinhacks_zod/packages/zod/src/index.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.colinhacks_zod.packages.zod.src.index');
var module = module || { id: 'third_party/javascript/colinhacks_zod/packages/zod/src/index.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_external_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.external");
const z = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.external');
exports.z = z;
const external_js_1 = z;
exports.setErrorMap = external_js_1.setErrorMap;
exports.getErrorMap = external_js_1.getErrorMap;
exports.defaultErrorMap = external_js_1.defaultErrorMap;
exports.addIssueToContext = external_js_1.addIssueToContext;
exports.makeIssue = external_js_1.makeIssue;
exports.EMPTY_PATH = external_js_1.EMPTY_PATH;
exports.ParseStatus = external_js_1.ParseStatus;
exports.INVALID = external_js_1.INVALID;
exports.DIRTY = external_js_1.DIRTY;
exports.OK = external_js_1.OK;
exports.isAborted = external_js_1.isAborted;
exports.isDirty = external_js_1.isDirty;
exports.isValid = external_js_1.isValid;
exports.isAsync = external_js_1.isAsync;
exports.util = external_js_1.util;
exports.objectUtil = external_js_1.objectUtil;
exports.ZodParsedType = external_js_1.ZodParsedType;
exports.getParsedType = external_js_1.getParsedType;
exports.datetimeRegex = external_js_1.datetimeRegex;
exports.custom = external_js_1.custom;
exports.ZodType = external_js_1.ZodType;
exports.ZodString = external_js_1.ZodString;
exports.ZodNumber = external_js_1.ZodNumber;
exports.ZodBigInt = external_js_1.ZodBigInt;
exports.ZodBoolean = external_js_1.ZodBoolean;
exports.ZodDate = external_js_1.ZodDate;
exports.ZodSymbol = external_js_1.ZodSymbol;
exports.ZodUndefined = external_js_1.ZodUndefined;
exports.ZodNull = external_js_1.ZodNull;
exports.ZodAny = external_js_1.ZodAny;
exports.ZodUnknown = external_js_1.ZodUnknown;
exports.ZodNever = external_js_1.ZodNever;
exports.ZodVoid = external_js_1.ZodVoid;
exports.ZodArray = external_js_1.ZodArray;
exports.ZodObject = external_js_1.ZodObject;
exports.ZodUnion = external_js_1.ZodUnion;
exports.ZodDiscriminatedUnion = external_js_1.ZodDiscriminatedUnion;
exports.ZodIntersection = external_js_1.ZodIntersection;
exports.ZodTuple = external_js_1.ZodTuple;
exports.ZodRecord = external_js_1.ZodRecord;
exports.ZodMap = external_js_1.ZodMap;
exports.ZodSet = external_js_1.ZodSet;
exports.ZodFunction = external_js_1.ZodFunction;
exports.ZodLazy = external_js_1.ZodLazy;
exports.ZodLiteral = external_js_1.ZodLiteral;
exports.ZodEnum = external_js_1.ZodEnum;
exports.ZodNativeEnum = external_js_1.ZodNativeEnum;
exports.ZodPromise = external_js_1.ZodPromise;
exports.ZodEffects = external_js_1.ZodEffects;
exports.ZodTransformer = external_js_1.ZodTransformer;
exports.ZodOptional = external_js_1.ZodOptional;
exports.ZodNullable = external_js_1.ZodNullable;
exports.ZodDefault = external_js_1.ZodDefault;
exports.ZodCatch = external_js_1.ZodCatch;
exports.ZodNaN = external_js_1.ZodNaN;
exports.BRAND = external_js_1.BRAND;
exports.ZodBranded = external_js_1.ZodBranded;
exports.ZodPipeline = external_js_1.ZodPipeline;
exports.ZodReadonly = external_js_1.ZodReadonly;
exports.Schema = external_js_1.Schema;
exports.ZodSchema = external_js_1.ZodSchema;
exports.late = external_js_1.late;
exports.ZodFirstPartyTypeKind = external_js_1.ZodFirstPartyTypeKind;
exports.coerce = external_js_1.coerce;
exports.any = external_js_1.any;
exports.array = external_js_1.array;
exports.bigint = external_js_1.bigint;
exports.boolean = external_js_1.boolean;
exports.date = external_js_1.date;
exports.discriminatedUnion = external_js_1.discriminatedUnion;
exports.effect = external_js_1.effect;
exports.enum = external_js_1.enum;
exports.function = external_js_1.function;
exports.instanceof = external_js_1.instanceof;
exports.intersection = external_js_1.intersection;
exports.lazy = external_js_1.lazy;
exports.literal = external_js_1.literal;
exports.map = external_js_1.map;
exports.nan = external_js_1.nan;
exports.nativeEnum = external_js_1.nativeEnum;
exports.never = external_js_1.never;
exports.null = external_js_1.null;
exports.nullable = external_js_1.nullable;
exports.number = external_js_1.number;
exports.object = external_js_1.object;
exports.oboolean = external_js_1.oboolean;
exports.onumber = external_js_1.onumber;
exports.optional = external_js_1.optional;
exports.ostring = external_js_1.ostring;
exports.pipeline = external_js_1.pipeline;
exports.preprocess = external_js_1.preprocess;
exports.promise = external_js_1.promise;
exports.record = external_js_1.record;
exports.set = external_js_1.set;
exports.strictObject = external_js_1.strictObject;
exports.string = external_js_1.string;
exports.symbol = external_js_1.symbol;
exports.transformer = external_js_1.transformer;
exports.tuple = external_js_1.tuple;
exports.undefined = external_js_1.undefined;
exports.union = external_js_1.union;
exports.unknown = external_js_1.unknown;
exports.void = external_js_1.void;
exports.NEVER = external_js_1.NEVER;
exports.ZodIssueCode = external_js_1.ZodIssueCode;
exports.quotelessJson = external_js_1.quotelessJson;
exports.ZodError = external_js_1.ZodError;
/** @typedef {!tsickle_external_1.ParseParams} */
exports.ParseParams; // re-export typedef
/** @typedef {!tsickle_external_1.ParsePathComponent} */
exports.ParsePathComponent; // re-export typedef
/** @typedef {!tsickle_external_1.ParsePath} */
exports.ParsePath; // re-export typedef
/** @typedef {!tsickle_external_1.ParseContext} */
exports.ParseContext; // re-export typedef
/** @typedef {!tsickle_external_1.ParseInput} */
exports.ParseInput; // re-export typedef
/** @typedef {!tsickle_external_1.ObjectPair} */
exports.ObjectPair; // re-export typedef
/** @typedef {!tsickle_external_1.ParseResult} */
exports.ParseResult; // re-export typedef
/** @typedef {!tsickle_external_1.SyncParseReturnType} */
exports.SyncParseReturnType; // re-export typedef
/** @typedef {!tsickle_external_1.AsyncParseReturnType} */
exports.AsyncParseReturnType; // re-export typedef
/** @typedef {!tsickle_external_1.ParseReturnType} */
exports.ParseReturnType; // re-export typedef
/** @typedef {!tsickle_external_1.Primitive} */
exports.Primitive; // re-export typedef
/** @typedef {!tsickle_external_1.Scalars} */
exports.Scalars; // re-export typedef
/** @typedef {!tsickle_external_1.RefinementCtx} */
exports.RefinementCtx; // re-export typedef
/** @typedef {!tsickle_external_1.ZodRawShape} */
exports.ZodRawShape; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTypeAny} */
exports.ZodTypeAny; // re-export typedef
/** @typedef {!tsickle_external_1.infer} */
exports.TypeOf; // re-export typedef
/** @typedef {!tsickle_external_1.input} */
exports.input; // re-export typedef
/** @typedef {!tsickle_external_1.output} */
exports.output; // re-export typedef
/** @typedef {!tsickle_external_1.infer} */
exports.infer; // re-export typedef
/** @typedef {!tsickle_external_1.CustomErrorParams} */
exports.CustomErrorParams; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTypeDef} */
exports.ZodTypeDef; // re-export typedef
/** @typedef {!tsickle_external_1.RawCreateParams} */
exports.RawCreateParams; // re-export typedef
/** @typedef {!tsickle_external_1.ProcessedCreateParams} */
exports.ProcessedCreateParams; // re-export typedef
/** @typedef {!tsickle_external_1.SafeParseSuccess} */
exports.SafeParseSuccess; // re-export typedef
/** @typedef {!tsickle_external_1.SafeParseError} */
exports.SafeParseError; // re-export typedef
/** @typedef {!tsickle_external_1.SafeParseReturnType} */
exports.SafeParseReturnType; // re-export typedef
/** @typedef {!tsickle_external_1.IpVersion} */
exports.IpVersion; // re-export typedef
/** @typedef {!tsickle_external_1.ZodStringCheck} */
exports.ZodStringCheck; // re-export typedef
/** @typedef {!tsickle_external_1.ZodStringDef} */
exports.ZodStringDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNumberCheck} */
exports.ZodNumberCheck; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNumberDef} */
exports.ZodNumberDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodBigIntCheck} */
exports.ZodBigIntCheck; // re-export typedef
/** @typedef {!tsickle_external_1.ZodBigIntDef} */
exports.ZodBigIntDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodBooleanDef} */
exports.ZodBooleanDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodDateCheck} */
exports.ZodDateCheck; // re-export typedef
/** @typedef {!tsickle_external_1.ZodDateDef} */
exports.ZodDateDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodSymbolDef} */
exports.ZodSymbolDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodUndefinedDef} */
exports.ZodUndefinedDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNullDef} */
exports.ZodNullDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodAnyDef} */
exports.ZodAnyDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodUnknownDef} */
exports.ZodUnknownDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNeverDef} */
exports.ZodNeverDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodVoidDef} */
exports.ZodVoidDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodArrayDef} */
exports.ZodArrayDef; // re-export typedef
/** @typedef {!tsickle_external_1.ArrayCardinality} */
exports.ArrayCardinality; // re-export typedef
/** @typedef {!tsickle_external_1.arrayOutputType} */
exports.arrayOutputType; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNonEmptyArray} */
exports.ZodNonEmptyArray; // re-export typedef
/** @typedef {!tsickle_external_1.UnknownKeysParam} */
exports.UnknownKeysParam; // re-export typedef
/** @typedef {!tsickle_external_1.ZodObjectDef} */
exports.ZodObjectDef; // re-export typedef
/** @typedef {!tsickle_external_1.mergeTypes} */
exports.mergeTypes; // re-export typedef
/** @typedef {!tsickle_external_1.objectOutputType} */
exports.objectOutputType; // re-export typedef
/** @typedef {!tsickle_external_1.baseObjectOutputType} */
exports.baseObjectOutputType; // re-export typedef
/** @typedef {!tsickle_external_1.objectInputType} */
exports.objectInputType; // re-export typedef
/** @typedef {!tsickle_external_1.baseObjectInputType} */
exports.baseObjectInputType; // re-export typedef
/** @typedef {!tsickle_external_1.CatchallOutput} */
exports.CatchallOutput; // re-export typedef
/** @typedef {!tsickle_external_1.CatchallInput} */
exports.CatchallInput; // re-export typedef
/** @typedef {!tsickle_external_1.PassthroughType} */
exports.PassthroughType; // re-export typedef
/** @typedef {!tsickle_external_1.deoptional} */
exports.deoptional; // re-export typedef
/** @typedef {!tsickle_external_1.SomeZodObject} */
exports.SomeZodObject; // re-export typedef
/** @typedef {!tsickle_external_1.noUnrecognized} */
exports.noUnrecognized; // re-export typedef
/** @typedef {!tsickle_external_1.AnyZodObject} */
exports.AnyZodObject; // re-export typedef
/** @typedef {!tsickle_external_1.ZodUnionOptions} */
exports.ZodUnionOptions; // re-export typedef
/** @typedef {!tsickle_external_1.ZodUnionDef} */
exports.ZodUnionDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodDiscriminatedUnionOption} */
exports.ZodDiscriminatedUnionOption; // re-export typedef
/** @typedef {!tsickle_external_1.ZodDiscriminatedUnionDef} */
exports.ZodDiscriminatedUnionDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodIntersectionDef} */
exports.ZodIntersectionDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTupleItems} */
exports.ZodTupleItems; // re-export typedef
/** @typedef {!tsickle_external_1.AssertArray} */
exports.AssertArray; // re-export typedef
/** @typedef {!tsickle_external_1.OutputTypeOfTuple} */
exports.OutputTypeOfTuple; // re-export typedef
/** @typedef {!tsickle_external_1.OutputTypeOfTupleWithRest} */
exports.OutputTypeOfTupleWithRest; // re-export typedef
/** @typedef {!tsickle_external_1.InputTypeOfTuple} */
exports.InputTypeOfTuple; // re-export typedef
/** @typedef {!tsickle_external_1.InputTypeOfTupleWithRest} */
exports.InputTypeOfTupleWithRest; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTupleDef} */
exports.ZodTupleDef; // re-export typedef
/** @typedef {!tsickle_external_1.AnyZodTuple} */
exports.AnyZodTuple; // re-export typedef
/** @typedef {!tsickle_external_1.ZodRecordDef} */
exports.ZodRecordDef; // re-export typedef
/** @typedef {!tsickle_external_1.KeySchema} */
exports.KeySchema; // re-export typedef
/** @typedef {!tsickle_external_1.RecordType} */
exports.RecordType; // re-export typedef
/** @typedef {!tsickle_external_1.ZodMapDef} */
exports.ZodMapDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodSetDef} */
exports.ZodSetDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodFunctionDef} */
exports.ZodFunctionDef; // re-export typedef
/** @typedef {!tsickle_external_1.OuterTypeOfFunction} */
exports.OuterTypeOfFunction; // re-export typedef
/** @typedef {!tsickle_external_1.InnerTypeOfFunction} */
exports.InnerTypeOfFunction; // re-export typedef
/** @typedef {!tsickle_external_1.ZodLazyDef} */
exports.ZodLazyDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodLiteralDef} */
exports.ZodLiteralDef; // re-export typedef
/** @typedef {!tsickle_external_1.ArrayKeys} */
exports.ArrayKeys; // re-export typedef
/** @typedef {!tsickle_external_1.Indices} */
exports.Indices; // re-export typedef
/** @typedef {!tsickle_external_1.EnumValues} */
exports.EnumValues; // re-export typedef
/** @typedef {!tsickle_external_1.Values} */
exports.Values; // re-export typedef
/** @typedef {!tsickle_external_1.ZodEnumDef} */
exports.ZodEnumDef; // re-export typedef
/** @typedef {!tsickle_external_1.Writeable} */
exports.Writeable; // re-export typedef
/** @typedef {!tsickle_external_1.FilterEnum} */
exports.FilterEnum; // re-export typedef
/** @typedef {!tsickle_external_1.typecast} */
exports.typecast; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNativeEnumDef} */
exports.ZodNativeEnumDef; // re-export typedef
/** @typedef {!tsickle_external_1.EnumLike} */
exports.EnumLike; // re-export typedef
/** @typedef {!tsickle_external_1.ZodPromiseDef} */
exports.ZodPromiseDef; // re-export typedef
/** @typedef {!tsickle_external_1.Refinement} */
exports.Refinement; // re-export typedef
/** @typedef {!tsickle_external_1.SuperRefinement} */
exports.SuperRefinement; // re-export typedef
/** @typedef {!tsickle_external_1.RefinementEffect} */
exports.RefinementEffect; // re-export typedef
/** @typedef {!tsickle_external_1.TransformEffect} */
exports.TransformEffect; // re-export typedef
/** @typedef {!tsickle_external_1.PreprocessEffect} */
exports.PreprocessEffect; // re-export typedef
/** @typedef {!tsickle_external_1.Effect} */
exports.Effect; // re-export typedef
/** @typedef {!tsickle_external_1.ZodEffectsDef} */
exports.ZodEffectsDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodOptionalDef} */
exports.ZodOptionalDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodOptionalType} */
exports.ZodOptionalType; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNullableDef} */
exports.ZodNullableDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNullableType} */
exports.ZodNullableType; // re-export typedef
/** @typedef {!tsickle_external_1.ZodDefaultDef} */
exports.ZodDefaultDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodCatchDef} */
exports.ZodCatchDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNaNDef} */
exports.ZodNaNDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodBrandedDef} */
exports.ZodBrandedDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodPipelineDef} */
exports.ZodPipelineDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodReadonlyDef} */
exports.ZodReadonlyDef; // re-export typedef
/** @typedef {!tsickle_external_1.ZodFirstPartySchemaTypes} */
exports.ZodFirstPartySchemaTypes; // re-export typedef
/** @typedef {!tsickle_external_1.inferFlattenedErrors} */
exports.inferFlattenedErrors; // re-export typedef
/** @typedef {!tsickle_external_1.typeToFlattenedError} */
exports.typeToFlattenedError; // re-export typedef
/** @typedef {!tsickle_external_1.ZodIssueBase} */
exports.ZodIssueBase; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidTypeIssue} */
exports.ZodInvalidTypeIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidLiteralIssue} */
exports.ZodInvalidLiteralIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodUnrecognizedKeysIssue} */
exports.ZodUnrecognizedKeysIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidUnionIssue} */
exports.ZodInvalidUnionIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidUnionDiscriminatorIssue} */
exports.ZodInvalidUnionDiscriminatorIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidEnumValueIssue} */
exports.ZodInvalidEnumValueIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidArgumentsIssue} */
exports.ZodInvalidArgumentsIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidReturnTypeIssue} */
exports.ZodInvalidReturnTypeIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidDateIssue} */
exports.ZodInvalidDateIssue; // re-export typedef
/** @typedef {!tsickle_external_1.StringValidation} */
exports.StringValidation; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidStringIssue} */
exports.ZodInvalidStringIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTooSmallIssue} */
exports.ZodTooSmallIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodTooBigIssue} */
exports.ZodTooBigIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodInvalidIntersectionTypesIssue} */
exports.ZodInvalidIntersectionTypesIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNotMultipleOfIssue} */
exports.ZodNotMultipleOfIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodNotFiniteIssue} */
exports.ZodNotFiniteIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodCustomIssue} */
exports.ZodCustomIssue; // re-export typedef
/** @typedef {!tsickle_external_1.DenormalizedError} */
exports.DenormalizedError; // re-export typedef
/** @typedef {!tsickle_external_1.ZodIssueOptionalMessage} */
exports.ZodIssueOptionalMessage; // re-export typedef
/** @typedef {!tsickle_external_1.ZodIssue} */
exports.ZodIssue; // re-export typedef
/** @typedef {!tsickle_external_1.ZodFormattedError} */
exports.ZodFormattedError; // re-export typedef
/** @typedef {!tsickle_external_1.inferFormattedError} */
exports.inferFormattedError; // re-export typedef
/** @typedef {!tsickle_external_1.IssueData} */
exports.IssueData; // re-export typedef
/** @typedef {!tsickle_external_1.ErrorMapCtx} */
exports.ErrorMapCtx; // re-export typedef
/** @typedef {!tsickle_external_1.ZodErrorMap} */
exports.ZodErrorMap; // re-export typedef
exports.default = z;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2024 Anthropic, PBC
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/modelcontextprotocol/src/types.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.modelcontextprotocol.src.types');
var module = module || { id: 'third_party/javascript/modelcontextprotocol/src/types.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_zod_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.index");
const tsickle_types_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.server.auth.types");
const zod_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.index');
/** @type {string} */
exports.LATEST_PROTOCOL_VERSION = "2025-06-18";
/** @type {string} */
exports.DEFAULT_NEGOTIATED_PROTOCOL_VERSION = "2025-03-26";
/** @type {!Array<string>} */
exports.SUPPORTED_PROTOCOL_VERSIONS = [
    exports.LATEST_PROTOCOL_VERSION,
    "2025-03-26",
    "2024-11-05",
    "2024-10-07",
];
/* JSON-RPC types */
/** @type {string} */
exports.JSONRPC_VERSION = "2.0";
/**
 * A progress token, used to associate progress notifications with the original request.
 * @type {!tsickle_zod_1.ZodUnion<!Array<?>>}
 */
exports.ProgressTokenSchema = zod_1.z.union([zod_1.z.string(), zod_1.z.number().int()]);
/**
 * An opaque token used to represent a cursor for pagination.
 * @type {!tsickle_zod_1.ZodString}
 */
exports.CursorSchema = zod_1.z.string();
/** @type {!tsickle_zod_1.ZodObject<{progressToken: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodUnion<!Array<?>>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
const RequestMetaSchema = zod_1.z
    .object({
    /**
     * If specified, the caller is requesting out-of-band progress notifications for this request (as represented by notifications/progress). The value of this parameter is an opaque token that will be attached to any subsequent notifications. The receiver is not obligated to provide these notifications.
     */
    progressToken: zod_1.z.optional(exports.ProgressTokenSchema),
})
    .passthrough();
/** @type {!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{progressToken: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodUnion<!Array<?>>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
const BaseRequestParamsSchema = zod_1.z
    .object({
    _meta: zod_1.z.optional(RequestMetaSchema),
})
    .passthrough();
/** @type {!tsickle_zod_1.ZodObject<{method: !tsickle_zod_1.ZodString, params: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{progressToken: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodUnion<!Array<?>>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.RequestSchema = zod_1.z.object({
    method: zod_1.z.string(),
    params: zod_1.z.optional(BaseRequestParamsSchema),
});
/** @type {!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
const BaseNotificationParamsSchema = zod_1.z
    .object({
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/** @type {!tsickle_zod_1.ZodObject<{method: !tsickle_zod_1.ZodString, params: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.NotificationSchema = zod_1.z.object({
    method: zod_1.z.string(),
    params: zod_1.z.optional(BaseNotificationParamsSchema),
});
/** @type {!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.ResultSchema = zod_1.z
    .object({
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * A uniquely identifying ID for a request in JSON-RPC.
 * @type {!tsickle_zod_1.ZodUnion<!Array<?>>}
 */
exports.RequestIdSchema = zod_1.z.union([zod_1.z.string(), zod_1.z.number().int()]);
/**
 * A request that expects a response.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.JSONRPCRequestSchema = zod_1.z
    .object({
    jsonrpc: zod_1.z.literal(exports.JSONRPC_VERSION),
    id: exports.RequestIdSchema,
})
    .merge(exports.RequestSchema)
    .strict();
/** @type {function(*): boolean} */
exports.isJSONRPCRequest = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.JSONRPCRequestSchema.safeParse(value).success);
/**
 * A notification which does not expect a response.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.JSONRPCNotificationSchema = zod_1.z
    .object({
    jsonrpc: zod_1.z.literal(exports.JSONRPC_VERSION),
})
    .merge(exports.NotificationSchema)
    .strict();
/** @type {function(*): boolean} */
exports.isJSONRPCNotification = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.JSONRPCNotificationSchema.safeParse(value).success);
/**
 * A successful (non-error) response to a request.
 * @type {!tsickle_zod_1.ZodObject<{jsonrpc: !tsickle_zod_1.ZodLiteral<string>, id: !tsickle_zod_1.ZodUnion<!Array<?>>, result: !tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.JSONRPCResponseSchema = zod_1.z
    .object({
    jsonrpc: zod_1.z.literal(exports.JSONRPC_VERSION),
    id: exports.RequestIdSchema,
    result: exports.ResultSchema,
})
    .strict();
/** @type {function(*): boolean} */
exports.isJSONRPCResponse = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.JSONRPCResponseSchema.safeParse(value).success);
/**
 * Error codes defined by the JSON-RPC specification.
 * @enum {number}
 */
var ErrorCode = {
    // SDK error codes
    ConnectionClosed: -32000,
    RequestTimeout: -32001,
    // Standard JSON-RPC error codes
    ParseError: -32700,
    InvalidRequest: -32600,
    MethodNotFound: -32601,
    InvalidParams: -32602,
    InternalError: -32603,
};
exports.ErrorCode = ErrorCode;
ErrorCode[ErrorCode.ConnectionClosed] = 'ConnectionClosed';
ErrorCode[ErrorCode.RequestTimeout] = 'RequestTimeout';
ErrorCode[ErrorCode.ParseError] = 'ParseError';
ErrorCode[ErrorCode.InvalidRequest] = 'InvalidRequest';
ErrorCode[ErrorCode.MethodNotFound] = 'MethodNotFound';
ErrorCode[ErrorCode.InvalidParams] = 'InvalidParams';
ErrorCode[ErrorCode.InternalError] = 'InternalError';
/**
 * A response to a request that indicates an error occurred.
 * @type {!tsickle_zod_1.ZodObject<{jsonrpc: !tsickle_zod_1.ZodLiteral<string>, id: !tsickle_zod_1.ZodUnion<!Array<?>>, error: !tsickle_zod_1.ZodObject<{code: !tsickle_zod_1.ZodNumber, message: !tsickle_zod_1.ZodString, data: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodUnknown>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.JSONRPCErrorSchema = zod_1.z
    .object({
    jsonrpc: zod_1.z.literal(exports.JSONRPC_VERSION),
    id: exports.RequestIdSchema,
    error: zod_1.z.object({
        /**
         * The error type that occurred.
         */
        code: zod_1.z.number().int(),
        /**
         * A short description of the error. The message SHOULD be limited to a concise single sentence.
         */
        message: zod_1.z.string(),
        /**
         * Additional information about the error. The value of this member is defined by the sender (e.g. detailed error information, nested errors etc.).
         */
        data: zod_1.z.optional(zod_1.z.unknown()),
    }),
})
    .strict();
/** @type {function(*): boolean} */
exports.isJSONRPCError = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.JSONRPCErrorSchema.safeParse(value).success);
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.JSONRPCMessageSchema = zod_1.z.union([
    exports.JSONRPCRequestSchema,
    exports.JSONRPCNotificationSchema,
    exports.JSONRPCResponseSchema,
    exports.JSONRPCErrorSchema,
]);
/* Empty result */
/**
 * A response that indicates success but carries no data.
 * @type {!tsickle_zod_1.ZodObject<{_meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.EmptyResultSchema = exports.ResultSchema.strict();
/* Cancellation */
/**
 * This notification can be sent by either side to indicate that it is cancelling a previously-issued request.
 *
 * The request SHOULD still be in-flight, but due to communication latency, it is always possible that this notification MAY arrive after the request has already finished.
 *
 * This notification indicates that the result will be unused, so any associated processing SHOULD cease.
 *
 * A client MUST NOT attempt to cancel its `initialize` request.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CancelledNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/cancelled"),
    params: BaseNotificationParamsSchema.extend({
        /**
         * The ID of the request to cancel.
         *
         * This MUST correspond to the ID of a request previously issued in the same direction.
         */
        requestId: exports.RequestIdSchema,
        /**
         * An optional string describing the reason for the cancellation. This MAY be logged or presented to the user.
         */
        reason: zod_1.z.string().optional(),
    }),
});
/* Base Metadata */
/**
 * Base metadata interface for common properties across resources, tools, prompts, and implementations.
 * @type {!tsickle_zod_1.ZodObject<{name: !tsickle_zod_1.ZodString, title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.BaseMetadataSchema = zod_1.z
    .object({
    /**
     * Intended for programmatic or logical use, but used as a display name in past specs or fallback
     */
    name: zod_1.z.string(),
    /**
     * Intended for UI and end-user contexts — optimized to be human-readable and easily understood,
     * even by those unfamiliar with domain-specific terminology.
     *
     * If not provided, the name should be used for display (except for Tool,
     * where `annotations.title` should be given precedence over using `name`,
     * if present).
     */
    title: zod_1.z.optional(zod_1.z.string()),
})
    .passthrough();
/* Initialization */
/**
 * Describes the name and version of an MCP implementation.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ImplementationSchema = exports.BaseMetadataSchema.extend({
    version: zod_1.z.string(),
});
/**
 * Capabilities a client may support. Known capabilities are defined here, in this schema, but this is not a closed set: any client can define its own, additional capabilities.
 * @type {!tsickle_zod_1.ZodObject<{experimental: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, sampling: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, elicitation: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, roots: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{listChanged: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ClientCapabilitiesSchema = zod_1.z
    .object({
    /**
     * Experimental, non-standard capabilities that the client supports.
     */
    experimental: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the client supports sampling from an LLM.
     */
    sampling: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the client supports eliciting user input.
     */
    elicitation: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the client supports listing roots.
     */
    roots: zod_1.z.optional(zod_1.z
        .object({
        /**
         * Whether the client supports issuing notifications for changes to the roots list.
         */
        listChanged: zod_1.z.optional(zod_1.z.boolean()),
    })
        .passthrough()),
})
    .passthrough();
/**
 * This request is sent from the client to the server when it first connects, asking it to begin initialization.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.InitializeRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("initialize"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The latest version of the Model Context Protocol that the client supports. The client MAY decide to support older versions as well.
         */
        protocolVersion: zod_1.z.string(),
        capabilities: exports.ClientCapabilitiesSchema,
        clientInfo: exports.ImplementationSchema,
    }),
});
/** @type {function(*): boolean} */
exports.isInitializeRequest = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.InitializeRequestSchema.safeParse(value).success);
/**
 * Capabilities that a server may support. Known capabilities are defined here, in this schema, but this is not a closed set: any server can define its own, additional capabilities.
 * @type {!tsickle_zod_1.ZodObject<{experimental: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, logging: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, completions: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, prompts: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{listChanged: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, resources: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{subscribe: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>, listChanged: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>, tools: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<{listChanged: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ServerCapabilitiesSchema = zod_1.z
    .object({
    /**
     * Experimental, non-standard capabilities that the server supports.
     */
    experimental: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the server supports sending log messages to the client.
     */
    logging: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the server supports sending completions to the client.
     */
    completions: zod_1.z.optional(zod_1.z.object({}).passthrough()),
    /**
     * Present if the server offers any prompt templates.
     */
    prompts: zod_1.z.optional(zod_1.z
        .object({
        /**
         * Whether this server supports issuing notifications for changes to the prompt list.
         */
        listChanged: zod_1.z.optional(zod_1.z.boolean()),
    })
        .passthrough()),
    /**
     * Present if the server offers any resources to read.
     */
    resources: zod_1.z.optional(zod_1.z
        .object({
        /**
         * Whether this server supports clients subscribing to resource updates.
         */
        subscribe: zod_1.z.optional(zod_1.z.boolean()),
        /**
         * Whether this server supports issuing notifications for changes to the resource list.
         */
        listChanged: zod_1.z.optional(zod_1.z.boolean()),
    })
        .passthrough()),
    /**
     * Present if the server offers any tools to call.
     */
    tools: zod_1.z.optional(zod_1.z
        .object({
        /**
         * Whether this server supports issuing notifications for changes to the tool list.
         */
        listChanged: zod_1.z.optional(zod_1.z.boolean()),
    })
        .passthrough()),
})
    .passthrough();
/**
 * After receiving an initialize request from the client, the server sends this response.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.InitializeResultSchema = exports.ResultSchema.extend({
    /**
     * The version of the Model Context Protocol that the server wants to use. This may not match the version that the client requested. If the client cannot support this version, it MUST disconnect.
     */
    protocolVersion: zod_1.z.string(),
    capabilities: exports.ServerCapabilitiesSchema,
    serverInfo: exports.ImplementationSchema,
    /**
     * Instructions describing how to use the server and its features.
     *
     * This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a "hint" to the model. For example, this information MAY be added to the system prompt.
     */
    instructions: zod_1.z.optional(zod_1.z.string()),
});
/**
 * This notification is sent from the client to the server after initialization has finished.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.InitializedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/initialized"),
});
/** @type {function(*): boolean} */
exports.isInitializedNotification = (/**
 * @param {*} value
 * @return {boolean}
 */
(value) => exports.InitializedNotificationSchema.safeParse(value).success);
/* Ping */
/**
 * A ping, issued by either the server or the client, to check that the other party is still alive. The receiver must promptly respond, or else may be disconnected.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PingRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("ping"),
});
/* Progress notifications */
/** @type {!tsickle_zod_1.ZodObject<{progress: !tsickle_zod_1.ZodNumber, total: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, message: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.ProgressSchema = zod_1.z
    .object({
    /**
     * The progress thus far. This should increase every time progress is made, even if the total is unknown.
     */
    progress: zod_1.z.number(),
    /**
     * Total number of items to process (or total progress required), if known.
     */
    total: zod_1.z.optional(zod_1.z.number()),
    /**
     * An optional message describing the current progress.
     */
    message: zod_1.z.optional(zod_1.z.string()),
})
    .passthrough();
/**
 * An out-of-band notification used to inform the receiver of a progress update for a long-running request.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ProgressNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/progress"),
    params: BaseNotificationParamsSchema.merge(exports.ProgressSchema).extend({
        /**
         * The progress token which was given in the initial request, used to associate this notification with the request that is proceeding.
         */
        progressToken: exports.ProgressTokenSchema,
    }),
});
/* Pagination */
/** @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.PaginatedRequestSchema = exports.RequestSchema.extend({
    params: BaseRequestParamsSchema.extend({
        /**
         * An opaque token representing the current pagination position.
         * If provided, the server should return results starting after this cursor.
         */
        cursor: zod_1.z.optional(exports.CursorSchema),
    }).optional(),
});
/** @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.PaginatedResultSchema = exports.ResultSchema.extend({
    /**
     * An opaque token representing the pagination position after the last returned result.
     * If present, there may be more results available.
     */
    nextCursor: zod_1.z.optional(exports.CursorSchema),
});
/* Resources */
/**
 * The contents of a specific resource or sub-resource.
 * @type {!tsickle_zod_1.ZodObject<{uri: !tsickle_zod_1.ZodString, mimeType: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceContentsSchema = zod_1.z
    .object({
    /**
     * The URI of this resource.
     */
    uri: zod_1.z.string(),
    /**
     * The MIME type of this resource, if known.
     */
    mimeType: zod_1.z.optional(zod_1.z.string()),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/** @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.TextResourceContentsSchema = exports.ResourceContentsSchema.extend({
    /**
     * The text of the item. This must only be set if the item can actually be represented as text (not binary data).
     */
    text: zod_1.z.string(),
});
/** @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>} */
exports.BlobResourceContentsSchema = exports.ResourceContentsSchema.extend({
    /**
     * A base64-encoded string representing the binary data of the item.
     */
    blob: zod_1.z.string(),
});
/**
 * A known resource that the server is capable of reading.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceSchema = exports.BaseMetadataSchema.extend({
    /**
     * The URI of this resource.
     */
    uri: zod_1.z.string(),
    /**
     * A description of what this resource represents.
     *
     * This can be used by clients to improve the LLM's understanding of available resources. It can be thought of like a "hint" to the model.
     */
    description: zod_1.z.optional(zod_1.z.string()),
    /**
     * The MIME type of this resource, if known.
     */
    mimeType: zod_1.z.optional(zod_1.z.string()),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
});
/**
 * A template description for resources available on the server.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceTemplateSchema = exports.BaseMetadataSchema.extend({
    /**
     * A URI template (according to RFC 6570) that can be used to construct resource URIs.
     */
    uriTemplate: zod_1.z.string(),
    /**
     * A description of what this template is for.
     *
     * This can be used by clients to improve the LLM's understanding of available resources. It can be thought of like a "hint" to the model.
     */
    description: zod_1.z.optional(zod_1.z.string()),
    /**
     * The MIME type for all resources that match this template. This should only be included if all resources matching this template have the same type.
     */
    mimeType: zod_1.z.optional(zod_1.z.string()),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
});
/**
 * Sent from the client to request a list of resources the server has.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListResourcesRequestSchema = exports.PaginatedRequestSchema.extend({
    method: zod_1.z.literal("resources/list"),
});
/**
 * The server's response to a resources/list request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListResourcesResultSchema = exports.PaginatedResultSchema.extend({
    resources: zod_1.z.array(exports.ResourceSchema),
});
/**
 * Sent from the client to request a list of resource templates the server has.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListResourceTemplatesRequestSchema = exports.PaginatedRequestSchema.extend({
    method: zod_1.z.literal("resources/templates/list"),
});
/**
 * The server's response to a resources/templates/list request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListResourceTemplatesResultSchema = exports.PaginatedResultSchema.extend({
    resourceTemplates: zod_1.z.array(exports.ResourceTemplateSchema),
});
/**
 * Sent from the client to the server, to read a specific resource URI.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ReadResourceRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("resources/read"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The URI of the resource to read. The URI can use any protocol; it is up to the server how to interpret it.
         */
        uri: zod_1.z.string(),
    }),
});
/**
 * The server's response to a resources/read request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ReadResourceResultSchema = exports.ResultSchema.extend({
    contents: zod_1.z.array(zod_1.z.union([exports.TextResourceContentsSchema, exports.BlobResourceContentsSchema])),
});
/**
 * An optional notification from the server to the client, informing it that the list of resources it can read from has changed. This may be issued by servers without any previous subscription from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceListChangedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/resources/list_changed"),
});
/**
 * Sent from the client to request resources/updated notifications from the server whenever a particular resource changes.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.SubscribeRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("resources/subscribe"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The URI of the resource to subscribe to. The URI can use any protocol; it is up to the server how to interpret it.
         */
        uri: zod_1.z.string(),
    }),
});
/**
 * Sent from the client to request cancellation of resources/updated notifications from the server. This should follow a previous resources/subscribe request.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.UnsubscribeRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("resources/unsubscribe"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The URI of the resource to unsubscribe from.
         */
        uri: zod_1.z.string(),
    }),
});
/**
 * A notification from the server to the client, informing it that a resource has changed and may need to be read again. This should only be sent if the client previously sent a resources/subscribe request.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceUpdatedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/resources/updated"),
    params: BaseNotificationParamsSchema.extend({
        /**
         * The URI of the resource that has been updated. This might be a sub-resource of the one that the client actually subscribed to.
         */
        uri: zod_1.z.string(),
    }),
});
/* Prompts */
/**
 * Describes an argument that a prompt can accept.
 * @type {!tsickle_zod_1.ZodObject<{name: !tsickle_zod_1.ZodString, description: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, required: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PromptArgumentSchema = zod_1.z
    .object({
    /**
     * The name of the argument.
     */
    name: zod_1.z.string(),
    /**
     * A human-readable description of the argument.
     */
    description: zod_1.z.optional(zod_1.z.string()),
    /**
     * Whether this argument must be provided.
     */
    required: zod_1.z.optional(zod_1.z.boolean()),
})
    .passthrough();
/**
 * A prompt or prompt template that the server offers.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PromptSchema = exports.BaseMetadataSchema.extend({
    /**
     * An optional description of what this prompt provides
     */
    description: zod_1.z.optional(zod_1.z.string()),
    /**
     * A list of arguments to use for templating the prompt.
     */
    arguments: zod_1.z.optional(zod_1.z.array(exports.PromptArgumentSchema)),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
});
/**
 * Sent from the client to request a list of prompts and prompt templates the server has.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListPromptsRequestSchema = exports.PaginatedRequestSchema.extend({
    method: zod_1.z.literal("prompts/list"),
});
/**
 * The server's response to a prompts/list request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListPromptsResultSchema = exports.PaginatedResultSchema.extend({
    prompts: zod_1.z.array(exports.PromptSchema),
});
/**
 * Used by the client to get a prompt provided by the server.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.GetPromptRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("prompts/get"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The name of the prompt or prompt template.
         */
        name: zod_1.z.string(),
        /**
         * Arguments to use for templating the prompt.
         */
        arguments: zod_1.z.optional(zod_1.z.record(zod_1.z.string())),
    }),
});
/**
 * Text provided to or from an LLM.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, text: !tsickle_zod_1.ZodString, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.TextContentSchema = zod_1.z
    .object({
    type: zod_1.z.literal("text"),
    /**
     * The text content of the message.
     */
    text: zod_1.z.string(),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * An image provided to or from an LLM.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, data: !tsickle_zod_1.ZodString, mimeType: !tsickle_zod_1.ZodString, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ImageContentSchema = zod_1.z
    .object({
    type: zod_1.z.literal("image"),
    /**
     * The base64-encoded image data.
     */
    data: zod_1.z.string(),
    /**
     * The MIME type of the image. Different providers may support different image types.
     */
    mimeType: zod_1.z.string(),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * An Audio provided to or from an LLM.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, data: !tsickle_zod_1.ZodString, mimeType: !tsickle_zod_1.ZodString, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.AudioContentSchema = zod_1.z
    .object({
    type: zod_1.z.literal("audio"),
    /**
     * The base64-encoded audio data.
     */
    data: zod_1.z.string(),
    /**
     * The MIME type of the audio. Different providers may support different audio types.
     */
    mimeType: zod_1.z.string(),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * The contents of a resource, embedded into a prompt or tool call result.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, resource: !tsickle_zod_1.ZodUnion<!Array<?>>, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.EmbeddedResourceSchema = zod_1.z
    .object({
    type: zod_1.z.literal("resource"),
    resource: zod_1.z.union([exports.TextResourceContentsSchema, exports.BlobResourceContentsSchema]),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * A resource that the server is capable of reading, included in a prompt or tool call result.
 *
 * Note: resource links returned by tools are not guaranteed to appear in the results of `resources/list` requests.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceLinkSchema = exports.ResourceSchema.extend({
    type: zod_1.z.literal("resource_link"),
});
/**
 * A content block that can be used in prompts and tool results.
 * @type {!tsickle_zod_1.ZodUnion<!Array<?>>}
 */
exports.ContentBlockSchema = zod_1.z.union([
    exports.TextContentSchema,
    exports.ImageContentSchema,
    exports.AudioContentSchema,
    exports.ResourceLinkSchema,
    exports.EmbeddedResourceSchema,
]);
/**
 * Describes a message returned as part of a prompt.
 * @type {!tsickle_zod_1.ZodObject<{role: !tsickle_zod_1.ZodEnum<!Array<?>>, content: !tsickle_zod_1.ZodUnion<!Array<?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PromptMessageSchema = zod_1.z
    .object({
    role: zod_1.z.enum(["user", "assistant"]),
    content: exports.ContentBlockSchema,
})
    .passthrough();
/**
 * The server's response to a prompts/get request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.GetPromptResultSchema = exports.ResultSchema.extend({
    /**
     * An optional description for the prompt.
     */
    description: zod_1.z.optional(zod_1.z.string()),
    messages: zod_1.z.array(exports.PromptMessageSchema),
});
/**
 * An optional notification from the server to the client, informing it that the list of prompts it offers has changed. This may be issued by servers without any previous subscription from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PromptListChangedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/prompts/list_changed"),
});
/* Tools */
/**
 * Additional properties describing a Tool to clients.
 *
 * NOTE: all properties in ToolAnnotations are **hints**.
 * They are not guaranteed to provide a faithful description of
 * tool behavior (including descriptive properties like `title`).
 *
 * Clients should never make tool use decisions based on ToolAnnotations
 * received from untrusted servers.
 * @type {!tsickle_zod_1.ZodObject<{title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, readOnlyHint: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>, destructiveHint: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>, idempotentHint: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>, openWorldHint: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ToolAnnotationsSchema = zod_1.z
    .object({
    /**
     * A human-readable title for the tool.
     */
    title: zod_1.z.optional(zod_1.z.string()),
    /**
     * If true, the tool does not modify its environment.
     *
     * Default: false
     */
    readOnlyHint: zod_1.z.optional(zod_1.z.boolean()),
    /**
     * If true, the tool may perform destructive updates to its environment.
     * If false, the tool performs only additive updates.
     *
     * (This property is meaningful only when `readOnlyHint == false`)
     *
     * Default: true
     */
    destructiveHint: zod_1.z.optional(zod_1.z.boolean()),
    /**
     * If true, calling the tool repeatedly with the same arguments
     * will have no additional effect on the its environment.
     *
     * (This property is meaningful only when `readOnlyHint == false`)
     *
     * Default: false
     */
    idempotentHint: zod_1.z.optional(zod_1.z.boolean()),
    /**
     * If true, this tool may interact with an "open world" of external
     * entities. If false, the tool's domain of interaction is closed.
     * For example, the world of a web search tool is open, whereas that
     * of a memory tool is not.
     *
     * Default: true
     */
    openWorldHint: zod_1.z.optional(zod_1.z.boolean()),
})
    .passthrough();
/**
 * Definition for a tool the client can call.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ToolSchema = exports.BaseMetadataSchema.extend({
    /**
     * A human-readable description of the tool.
     */
    description: zod_1.z.optional(zod_1.z.string()),
    /**
     * A JSON Schema object defining the expected parameters for the tool.
     */
    inputSchema: zod_1.z
        .object({
        type: zod_1.z.literal("object"),
        properties: zod_1.z.optional(zod_1.z.object({}).passthrough()),
        required: zod_1.z.optional(zod_1.z.array(zod_1.z.string())),
    })
        .passthrough(),
    /**
     * An optional JSON Schema object defining the structure of the tool's output returned in
     * the structuredContent field of a CallToolResult.
     */
    outputSchema: zod_1.z.optional(zod_1.z.object({
        type: zod_1.z.literal("object"),
        properties: zod_1.z.optional(zod_1.z.object({}).passthrough()),
        required: zod_1.z.optional(zod_1.z.array(zod_1.z.string())),
    })
        .passthrough()),
    /**
     * Optional additional tool information.
     */
    annotations: zod_1.z.optional(exports.ToolAnnotationsSchema),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
});
/**
 * Sent from the client to request a list of tools the server has.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListToolsRequestSchema = exports.PaginatedRequestSchema.extend({
    method: zod_1.z.literal("tools/list"),
});
/**
 * The server's response to a tools/list request from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListToolsResultSchema = exports.PaginatedResultSchema.extend({
    tools: zod_1.z.array(exports.ToolSchema),
});
/**
 * The server's response to a tool call.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CallToolResultSchema = exports.ResultSchema.extend({
    /**
     * A list of content objects that represent the result of the tool call.
     *
     * If the Tool does not define an outputSchema, this field MUST be present in the result.
     * For backwards compatibility, this field is always present, but it may be empty.
     */
    content: zod_1.z.array(exports.ContentBlockSchema).default([]),
    /**
     * An object containing structured tool output.
     *
     * If the Tool defines an outputSchema, this field MUST be present in the result, and contain a JSON object that matches the schema.
     */
    structuredContent: zod_1.z.object({}).passthrough().optional(),
    /**
     * Whether the tool call ended in an error.
     *
     * If not set, this is assumed to be false (the call was successful).
     *
     * Any errors that originate from the tool SHOULD be reported inside the result
     * object, with `isError` set to true, _not_ as an MCP protocol-level error
     * response. Otherwise, the LLM would not be able to see that an error occurred
     * and self-correct.
     *
     * However, any errors in _finding_ the tool, an error indicating that the
     * server does not support tool calls, or any other exceptional conditions,
     * should be reported as an MCP error response.
     */
    isError: zod_1.z.optional(zod_1.z.boolean()),
});
/**
 * CallToolResultSchema extended with backwards compatibility to protocol version 2024-10-07.
 * @type {!tsickle_zod_1.ZodUnion<!Array<?>>}
 */
exports.CompatibilityCallToolResultSchema = exports.CallToolResultSchema.or(exports.ResultSchema.extend({
    toolResult: zod_1.z.unknown(),
}));
/**
 * Used by the client to invoke a tool provided by the server.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CallToolRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("tools/call"),
    params: BaseRequestParamsSchema.extend({
        name: zod_1.z.string(),
        arguments: zod_1.z.optional(zod_1.z.record(zod_1.z.unknown())),
    }),
});
/**
 * An optional notification from the server to the client, informing it that the list of tools it offers has changed. This may be issued by servers without any previous subscription from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ToolListChangedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/tools/list_changed"),
});
/* Logging */
/**
 * The severity of a log message.
 * @type {!tsickle_zod_1.ZodEnum<!Array<?>>}
 */
exports.LoggingLevelSchema = zod_1.z.enum([
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
]);
/**
 * A request from the client to the server, to enable or adjust logging.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.SetLevelRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("logging/setLevel"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The level of logging that the client wants to receive from the server. The server should send all logs at this level and higher (i.e., more severe) to the client as notifications/logging/message.
         */
        level: exports.LoggingLevelSchema,
    }),
});
/**
 * Notification of a log message passed from server to client. If no logging/setLevel request has been sent from the client, the server MAY decide which messages to send automatically.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.LoggingMessageNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/message"),
    params: BaseNotificationParamsSchema.extend({
        /**
         * The severity of this log message.
         */
        level: exports.LoggingLevelSchema,
        /**
         * An optional name of the logger issuing this message.
         */
        logger: zod_1.z.optional(zod_1.z.string()),
        /**
         * The data to be logged, such as a string message or an object. Any JSON serializable type is allowed here.
         */
        data: zod_1.z.unknown(),
    }),
});
/* Sampling */
/**
 * Hints to use for model selection.
 * @type {!tsickle_zod_1.ZodObject<{name: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ModelHintSchema = zod_1.z
    .object({
    /**
     * A hint for a model name.
     */
    name: zod_1.z.string().optional(),
})
    .passthrough();
/**
 * The server's preferences for model selection, requested of the client during sampling.
 * @type {!tsickle_zod_1.ZodObject<{hints: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodArray<!tsickle_zod_1.ZodObject<{name: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>, string>>, costPriority: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, speedPriority: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, intelligencePriority: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ModelPreferencesSchema = zod_1.z
    .object({
    /**
     * Optional hints to use for model selection.
     */
    hints: zod_1.z.optional(zod_1.z.array(exports.ModelHintSchema)),
    /**
     * How much to prioritize cost when selecting a model.
     */
    costPriority: zod_1.z.optional(zod_1.z.number().min(0).max(1)),
    /**
     * How much to prioritize sampling speed (latency) when selecting a model.
     */
    speedPriority: zod_1.z.optional(zod_1.z.number().min(0).max(1)),
    /**
     * How much to prioritize intelligence and capabilities when selecting a model.
     */
    intelligencePriority: zod_1.z.optional(zod_1.z.number().min(0).max(1)),
})
    .passthrough();
/**
 * Describes a message issued to or received from an LLM API.
 * @type {!tsickle_zod_1.ZodObject<{role: !tsickle_zod_1.ZodEnum<!Array<?>>, content: !tsickle_zod_1.ZodUnion<!Array<?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.SamplingMessageSchema = zod_1.z
    .object({
    role: zod_1.z.enum(["user", "assistant"]),
    content: zod_1.z.union([exports.TextContentSchema, exports.ImageContentSchema, exports.AudioContentSchema]),
})
    .passthrough();
/**
 * A request from the server to sample an LLM via the client. The client has full discretion over which model to select. The client should also inform the user before beginning sampling, to allow them to inspect the request (human in the loop) and decide whether to approve it.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CreateMessageRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("sampling/createMessage"),
    params: BaseRequestParamsSchema.extend({
        messages: zod_1.z.array(exports.SamplingMessageSchema),
        /**
         * An optional system prompt the server wants to use for sampling. The client MAY modify or omit this prompt.
         */
        systemPrompt: zod_1.z.optional(zod_1.z.string()),
        /**
         * A request to include context from one or more MCP servers (including the caller), to be attached to the prompt. The client MAY ignore this request.
         */
        includeContext: zod_1.z.optional(zod_1.z.enum(["none", "thisServer", "allServers"])),
        temperature: zod_1.z.optional(zod_1.z.number()),
        /**
         * The maximum number of tokens to sample, as requested by the server. The client MAY choose to sample fewer tokens than requested.
         */
        maxTokens: zod_1.z.number().int(),
        stopSequences: zod_1.z.optional(zod_1.z.array(zod_1.z.string())),
        /**
         * Optional metadata to pass through to the LLM provider. The format of this metadata is provider-specific.
         */
        metadata: zod_1.z.optional(zod_1.z.object({}).passthrough()),
        /**
         * The server's preferences for which model to select.
         */
        modelPreferences: zod_1.z.optional(exports.ModelPreferencesSchema),
    }),
});
/**
 * The client's response to a sampling/create_message request from the server. The client should inform the user before returning the sampled message, to allow them to inspect the response (human in the loop) and decide whether to allow the server to see it.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CreateMessageResultSchema = exports.ResultSchema.extend({
    /**
     * The name of the model that generated the message.
     */
    model: zod_1.z.string(),
    /**
     * The reason why sampling stopped.
     */
    stopReason: zod_1.z.optional(zod_1.z.enum(["endTurn", "stopSequence", "maxTokens"]).or(zod_1.z.string())),
    role: zod_1.z.enum(["user", "assistant"]),
    content: zod_1.z.discriminatedUnion("type", [
        exports.TextContentSchema,
        exports.ImageContentSchema,
        exports.AudioContentSchema
    ]),
});
/* Elicitation */
/**
 * Primitive schema definition for boolean fields.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, description: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, default: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodBoolean>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.BooleanSchemaSchema = zod_1.z
    .object({
    type: zod_1.z.literal("boolean"),
    title: zod_1.z.optional(zod_1.z.string()),
    description: zod_1.z.optional(zod_1.z.string()),
    default: zod_1.z.optional(zod_1.z.boolean()),
})
    .passthrough();
/**
 * Primitive schema definition for string fields.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, description: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, minLength: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, maxLength: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, format: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodEnum<!Array<?>>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.StringSchemaSchema = zod_1.z
    .object({
    type: zod_1.z.literal("string"),
    title: zod_1.z.optional(zod_1.z.string()),
    description: zod_1.z.optional(zod_1.z.string()),
    minLength: zod_1.z.optional(zod_1.z.number()),
    maxLength: zod_1.z.optional(zod_1.z.number()),
    format: zod_1.z.optional(zod_1.z.enum(["email", "uri", "date", "date-time"])),
})
    .passthrough();
/**
 * Primitive schema definition for number fields.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodEnum<!Array<?>>, title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, description: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, minimum: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>, maximum: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodNumber>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.NumberSchemaSchema = zod_1.z
    .object({
    type: zod_1.z.enum(["number", "integer"]),
    title: zod_1.z.optional(zod_1.z.string()),
    description: zod_1.z.optional(zod_1.z.string()),
    minimum: zod_1.z.optional(zod_1.z.number()),
    maximum: zod_1.z.optional(zod_1.z.number()),
})
    .passthrough();
/**
 * Primitive schema definition for enum fields.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, title: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, description: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, enum: !tsickle_zod_1.ZodArray<!tsickle_zod_1.ZodString, string>, enumNames: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodArray<!tsickle_zod_1.ZodString, string>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.EnumSchemaSchema = zod_1.z
    .object({
    type: zod_1.z.literal("string"),
    title: zod_1.z.optional(zod_1.z.string()),
    description: zod_1.z.optional(zod_1.z.string()),
    enum: zod_1.z.array(zod_1.z.string()),
    enumNames: zod_1.z.optional(zod_1.z.array(zod_1.z.string())),
})
    .passthrough();
/**
 * Union of all primitive schema definitions.
 * @type {!tsickle_zod_1.ZodUnion<!Array<?>>}
 */
exports.PrimitiveSchemaDefinitionSchema = zod_1.z.union([
    exports.BooleanSchemaSchema,
    exports.StringSchemaSchema,
    exports.NumberSchemaSchema,
    exports.EnumSchemaSchema,
]);
/**
 * A request from the server to elicit user input via the client.
 * The client should present the message and form fields to the user.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ElicitRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("elicitation/create"),
    params: BaseRequestParamsSchema.extend({
        /**
         * The message to present to the user.
         */
        message: zod_1.z.string(),
        /**
         * The schema for the requested user input.
         */
        requestedSchema: zod_1.z
            .object({
            type: zod_1.z.literal("object"),
            properties: zod_1.z.record(zod_1.z.string(), exports.PrimitiveSchemaDefinitionSchema),
            required: zod_1.z.optional(zod_1.z.array(zod_1.z.string())),
        })
            .passthrough(),
    }),
});
/**
 * The client's response to an elicitation/create request from the server.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ElicitResultSchema = exports.ResultSchema.extend({
    /**
     * The user's response action.
     */
    action: zod_1.z.enum(["accept", "reject", "cancel"]),
    /**
     * The collected user input content (only present if action is "accept").
     */
    content: zod_1.z.optional(zod_1.z.record(zod_1.z.string(), zod_1.z.unknown())),
});
/* Autocomplete */
/**
 * A reference to a resource or resource template definition.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, uri: !tsickle_zod_1.ZodString}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceTemplateReferenceSchema = zod_1.z
    .object({
    type: zod_1.z.literal("ref/resource"),
    /**
     * The URI or URI template of the resource.
     */
    uri: zod_1.z.string(),
})
    .passthrough();
/**
 * @deprecated Use ResourceTemplateReferenceSchema instead
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, uri: !tsickle_zod_1.ZodString}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ResourceReferenceSchema = exports.ResourceTemplateReferenceSchema;
/**
 * Identifies a prompt.
 * @type {!tsickle_zod_1.ZodObject<{type: !tsickle_zod_1.ZodLiteral<string>, name: !tsickle_zod_1.ZodString}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.PromptReferenceSchema = zod_1.z
    .object({
    type: zod_1.z.literal("ref/prompt"),
    /**
     * The name of the prompt or prompt template
     */
    name: zod_1.z.string(),
})
    .passthrough();
/**
 * A request from the client to the server, to ask for completion options.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CompleteRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("completion/complete"),
    params: BaseRequestParamsSchema.extend({
        ref: zod_1.z.union([exports.PromptReferenceSchema, exports.ResourceTemplateReferenceSchema]),
        /**
         * The argument's information
         */
        argument: zod_1.z
            .object({
            /**
             * The name of the argument
             */
            name: zod_1.z.string(),
            /**
             * The value of the argument to use for completion matching.
             */
            value: zod_1.z.string(),
        })
            .passthrough(),
        context: zod_1.z.optional(zod_1.z.object({
            /**
             * Previously-resolved variables in a URI template or prompt.
             */
            arguments: zod_1.z.optional(zod_1.z.record(zod_1.z.string(), zod_1.z.string())),
        })),
    }),
});
/**
 * The server's response to a completion/complete request
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.CompleteResultSchema = exports.ResultSchema.extend({
    completion: zod_1.z
        .object({
        /**
         * An array of completion values. Must not exceed 100 items.
         */
        values: zod_1.z.array(zod_1.z.string()).max(100),
        /**
         * The total number of completion options available. This can exceed the number of values actually sent in the response.
         */
        total: zod_1.z.optional(zod_1.z.number().int()),
        /**
         * Indicates whether there are additional completion options beyond those provided in the current response, even if the exact total is unknown.
         */
        hasMore: zod_1.z.optional(zod_1.z.boolean()),
    })
        .passthrough(),
});
/* Roots */
/**
 * Represents a root directory or file that the server can operate on.
 * @type {!tsickle_zod_1.ZodObject<{uri: !tsickle_zod_1.ZodString, name: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodString>, _meta: !tsickle_zod_1.ZodOptional<!tsickle_zod_1.ZodObject<*, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>>}, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.RootSchema = zod_1.z
    .object({
    /**
     * The URI identifying the root. This *must* start with file:// for now.
     */
    uri: zod_1.z.string().startsWith("file://"),
    /**
     * An optional name for the root.
     */
    name: zod_1.z.optional(zod_1.z.string()),
    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: zod_1.z.optional(zod_1.z.object({}).passthrough()),
})
    .passthrough();
/**
 * Sent from the server to request a list of root URIs from the client.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListRootsRequestSchema = exports.RequestSchema.extend({
    method: zod_1.z.literal("roots/list"),
});
/**
 * The client's response to a roots/list request from the server.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.ListRootsResultSchema = exports.ResultSchema.extend({
    roots: zod_1.z.array(exports.RootSchema),
});
/**
 * A notification from the client to the server, informing it that the list of roots has changed.
 * @type {!tsickle_zod_1.ZodObject<?, string, !tsickle_zod_1.ZodSchema<?, ?, ?>, ?, ?>}
 */
exports.RootsListChangedNotificationSchema = exports.NotificationSchema.extend({
    method: zod_1.z.literal("notifications/roots/list_changed"),
});
/* Client messages */
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ClientRequestSchema = zod_1.z.union([
    exports.PingRequestSchema,
    exports.InitializeRequestSchema,
    exports.CompleteRequestSchema,
    exports.SetLevelRequestSchema,
    exports.GetPromptRequestSchema,
    exports.ListPromptsRequestSchema,
    exports.ListResourcesRequestSchema,
    exports.ListResourceTemplatesRequestSchema,
    exports.ReadResourceRequestSchema,
    exports.SubscribeRequestSchema,
    exports.UnsubscribeRequestSchema,
    exports.CallToolRequestSchema,
    exports.ListToolsRequestSchema,
]);
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ClientNotificationSchema = zod_1.z.union([
    exports.CancelledNotificationSchema,
    exports.ProgressNotificationSchema,
    exports.InitializedNotificationSchema,
    exports.RootsListChangedNotificationSchema,
]);
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ClientResultSchema = zod_1.z.union([
    exports.EmptyResultSchema,
    exports.CreateMessageResultSchema,
    exports.ElicitResultSchema,
    exports.ListRootsResultSchema,
]);
/* Server messages */
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ServerRequestSchema = zod_1.z.union([
    exports.PingRequestSchema,
    exports.CreateMessageRequestSchema,
    exports.ElicitRequestSchema,
    exports.ListRootsRequestSchema,
]);
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ServerNotificationSchema = zod_1.z.union([
    exports.CancelledNotificationSchema,
    exports.ProgressNotificationSchema,
    exports.LoggingMessageNotificationSchema,
    exports.ResourceUpdatedNotificationSchema,
    exports.ResourceListChangedNotificationSchema,
    exports.ToolListChangedNotificationSchema,
    exports.PromptListChangedNotificationSchema,
]);
/** @type {!tsickle_zod_1.ZodUnion<!Array<?>>} */
exports.ServerResultSchema = zod_1.z.union([
    exports.EmptyResultSchema,
    exports.InitializeResultSchema,
    exports.CompleteResultSchema,
    exports.GetPromptResultSchema,
    exports.ListPromptsResultSchema,
    exports.ListResourcesResultSchema,
    exports.ListResourceTemplatesResultSchema,
    exports.ReadResourceResultSchema,
    exports.CallToolResultSchema,
    exports.ListToolsResultSchema,
]);
/**
 * @extends {Error}
 */
class McpError extends Error {
    /**
     * @public
     * @param {number} code
     * @param {string} message
     * @param {*=} data
     */
    constructor(code, message, data) {
        super(`MCP error ${code}: ${message}`);
        this.code = code;
        this.data = data;
        this.name = "McpError";
    }
}
exports.McpError = McpError;
/* istanbul ignore if */
if (false) {
    /**
     * @const {number}
     * @public
     */
    McpError.prototype.code;
    /**
     * @const {*}
     * @public
     */
    McpError.prototype.data;
}
/** @typedef {(undefined|null|string|number|bigint|boolean)} */
var Primitive;
/** @typedef {?} */
var Flatten;
/** @typedef {?} */
var Infer;
/**
 * Headers that are compatible with both Node.js and the browser.
 * @typedef {?}
 */
exports.IsomorphicHeaders;
/**
 * Information about the incoming request.
 * @record
 */
function RequestInfo() { }
exports.RequestInfo = RequestInfo;
/* istanbul ignore if */
if (false) {
    /**
     * The headers of the request.
     * @type {?}
     * @public
     */
    RequestInfo.prototype.headers;
}
/**
 * Extra information about a message.
 * @record
 */
function MessageExtraInfo() { }
exports.MessageExtraInfo = MessageExtraInfo;
/* istanbul ignore if */
if (false) {
    /**
     * The request information.
     * @type {(undefined|!RequestInfo)}
     * @public
     */
    MessageExtraInfo.prototype.requestInfo;
    /**
     * The authentication information.
     * @type {(undefined|!tsickle_types_2.AuthInfo)}
     * @public
     */
    MessageExtraInfo.prototype.authInfo;
}
/** @typedef {(string|number)} */
exports.ProgressToken;
/** @typedef {string} */
exports.Cursor;
/** @typedef {?} */
exports.Request;
/** @typedef {?} */
exports.RequestMeta;
/** @typedef {?} */
exports.Notification;
/** @typedef {?} */
exports.Result;
/** @typedef {(string|number)} */
exports.RequestId;
/** @typedef {?} */
exports.JSONRPCRequest;
/** @typedef {?} */
exports.JSONRPCNotification;
/** @typedef {?} */
exports.JSONRPCResponse;
/** @typedef {?} */
exports.JSONRPCError;
/** @typedef {?} */
exports.JSONRPCMessage;
/** @typedef {?} */
exports.EmptyResult;
/** @typedef {?} */
exports.CancelledNotification;
/** @typedef {?} */
exports.BaseMetadata;
/** @typedef {?} */
exports.Implementation;
/** @typedef {?} */
exports.ClientCapabilities;
/** @typedef {?} */
exports.InitializeRequest;
/** @typedef {?} */
exports.ServerCapabilities;
/** @typedef {?} */
exports.InitializeResult;
/** @typedef {?} */
exports.InitializedNotification;
/** @typedef {?} */
exports.PingRequest;
/** @typedef {?} */
exports.Progress;
/** @typedef {?} */
exports.ProgressNotification;
/** @typedef {?} */
exports.PaginatedRequest;
/** @typedef {?} */
exports.PaginatedResult;
/** @typedef {?} */
exports.ResourceContents;
/** @typedef {?} */
exports.TextResourceContents;
/** @typedef {?} */
exports.BlobResourceContents;
/** @typedef {?} */
exports.Resource;
/** @typedef {?} */
exports.ResourceTemplate;
/** @typedef {?} */
exports.ListResourcesRequest;
/** @typedef {?} */
exports.ListResourcesResult;
/** @typedef {?} */
exports.ListResourceTemplatesRequest;
/** @typedef {?} */
exports.ListResourceTemplatesResult;
/** @typedef {?} */
exports.ReadResourceRequest;
/** @typedef {?} */
exports.ReadResourceResult;
/** @typedef {?} */
exports.ResourceListChangedNotification;
/** @typedef {?} */
exports.SubscribeRequest;
/** @typedef {?} */
exports.UnsubscribeRequest;
/** @typedef {?} */
exports.ResourceUpdatedNotification;
/** @typedef {?} */
exports.PromptArgument;
/** @typedef {?} */
exports.Prompt;
/** @typedef {?} */
exports.ListPromptsRequest;
/** @typedef {?} */
exports.ListPromptsResult;
/** @typedef {?} */
exports.GetPromptRequest;
/** @typedef {?} */
exports.TextContent;
/** @typedef {?} */
exports.ImageContent;
/** @typedef {?} */
exports.AudioContent;
/** @typedef {?} */
exports.EmbeddedResource;
/** @typedef {?} */
exports.ResourceLink;
/** @typedef {?} */
exports.ContentBlock;
/** @typedef {?} */
exports.PromptMessage;
/** @typedef {?} */
exports.GetPromptResult;
/** @typedef {?} */
exports.PromptListChangedNotification;
/** @typedef {?} */
exports.ToolAnnotations;
/** @typedef {?} */
exports.Tool;
/** @typedef {?} */
exports.ListToolsRequest;
/** @typedef {?} */
exports.ListToolsResult;
/** @typedef {?} */
exports.CallToolResult;
/** @typedef {?} */
exports.CompatibilityCallToolResult;
/** @typedef {?} */
exports.CallToolRequest;
/** @typedef {?} */
exports.ToolListChangedNotification;
/** @typedef {string} */
exports.LoggingLevel;
/** @typedef {?} */
exports.SetLevelRequest;
/** @typedef {?} */
exports.LoggingMessageNotification;
/** @typedef {?} */
exports.SamplingMessage;
/** @typedef {?} */
exports.CreateMessageRequest;
/** @typedef {?} */
exports.CreateMessageResult;
/** @typedef {?} */
exports.BooleanSchema;
/** @typedef {?} */
exports.StringSchema;
/** @typedef {?} */
exports.NumberSchema;
/** @typedef {?} */
exports.EnumSchema;
/** @typedef {?} */
exports.PrimitiveSchemaDefinition;
/** @typedef {?} */
exports.ElicitRequest;
/** @typedef {?} */
exports.ElicitResult;
/** @typedef {?} */
exports.ResourceTemplateReference;
/**
 * @deprecated Use ResourceTemplateReference instead
 * @typedef {?}
 */
exports.ResourceReference;
/** @typedef {?} */
exports.PromptReference;
/** @typedef {?} */
exports.CompleteRequest;
/** @typedef {?} */
exports.CompleteResult;
/** @typedef {?} */
exports.Root;
/** @typedef {?} */
exports.ListRootsRequest;
/** @typedef {?} */
exports.ListRootsResult;
/** @typedef {?} */
exports.RootsListChangedNotification;
/** @typedef {?} */
exports.ClientRequest;
/** @typedef {?} */
exports.ClientNotification;
/** @typedef {?} */
exports.ClientResult;
/** @typedef {?} */
exports.ServerRequest;
/** @typedef {?} */
exports.ServerNotification;
/** @typedef {?} */
exports.ServerResult;

;return exports;});
goog.loadModule(function(exports) {'use strict';// THIS FILE IS GENERATED, DO NOT MODIFY.
goog.module('google3.third_party.javascript.typings.node.node.child_process');
/**
* @type {?}
*/
exports = (/** @type {!function(string): ?} */(
typeof require === 'function' ? require : function(s) { return { }; }
))('child_process');

;return exports;});
goog.loadModule(function(exports) {'use strict';// THIS FILE IS GENERATED, DO NOT MODIFY.
goog.module('google3.third_party.javascript.typings.node.node.string_decoder');
/**
* @type {?}
*/
exports = (/** @type {!function(string): ?} */(
typeof require === 'function' ? require : function(s) { return { }; }
))('string_decoder');

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/stdio_transport.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.stdio_transport');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/stdio_transport.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_transport_1 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.shared.transport");
const tsickle_types_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.types");
const tsickle_child_process_3 = goog.requireType("google3.third_party.javascript.typings.node.node.child_process");
const tsickle_string_decoder_4 = goog.requireType("google3.third_party.javascript.typings.node.node.string_decoder");
const types_js_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.types');
const child_process_1 = goog.require('google3.third_party.javascript.typings.node.node.child_process');
const string_decoder_1 = goog.require('google3.third_party.javascript.typings.node.node.string_decoder');
/**
 * Buffers a continuous byte stream into discrete newline-delimited JSON-RPC messages.
 */
class ReadBuffer {
    constructor() {
        this.buffer = '';
        this.decoder = new string_decoder_1.StringDecoder('utf8');
    }
    /**
     * @public
     * @param {?} chunk
     * @return {void}
     */
    append(chunk) {
        this.buffer += this.decoder.write(chunk);
    }
    /**
     * @public
     * @return {(null|?)}
     */
    readMessage() {
        if (!this.buffer) {
            return null;
        }
        /** @type {number} */
        const index = this.buffer.indexOf('\n');
        if (index === -1) {
            return null;
        }
        /** @type {string} */
        const line = this.buffer.slice(0, index).replace(/\r$/, '');
        this.buffer = this.buffer.slice(index + 1);
        return deserializeMessage(line);
    }
    /**
     * @public
     * @return {void}
     */
    clear() {
        this.buffer = '';
        this.decoder = new string_decoder_1.StringDecoder('utf8');
    }
}
exports.ReadBuffer = ReadBuffer;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @private
     */
    ReadBuffer.prototype.buffer;
    /**
     * @type {!tsickle_string_decoder_4.StringDecoder}
     * @private
     */
    ReadBuffer.prototype.decoder;
}
/**
 * @param {string} line
 * @return {?}
 */
function deserializeMessage(line) {
    return types_js_1.JSONRPCMessageSchema.parse(JSON.parse(line));
}
/**
 * @param {?} message
 * @return {string}
 */
function serializeMessage(message) {
    return JSON.stringify(message) + '\n';
}
/**
 * Server transport for stdio: communicates with an MCP client by reading from
 * `process.stdin` and writing to `process.stdout`.
 * @implements {tsickle_transport_1.Transport}
 */
class StdioServerTransport {
    /**
     * @public
     * @param {!NodeJS.ReadStream=} stdin
     * @param {!NodeJS.WriteStream=} stdout
     */
    constructor(stdin = process.stdin, stdout = process.stdout) {
        this.stdin = stdin;
        this.stdout = stdout;
        this.readBuffer = new ReadBuffer();
        this.started = false;
        this.onData = (/**
         * @param {?} chunk
         * @return {void}
         */
        (chunk) => {
            this.readBuffer.append(chunk);
            this.processReadBuffer();
        });
        this.onError = (/**
         * @param {!Error} error
         * @return {void}
         */
        (error) => {
            this.onerror?.(error);
        });
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async start() {
        if (this.started) {
            throw new Error('StdioServerTransport already started! If using Server class, note that connect() calls start() automatically.');
        }
        this.started = true;
        this.stdin.on('data', this.onData);
        this.stdin.on('error', this.onError);
    }
    /**
     * @private
     * @return {void}
     */
    processReadBuffer() {
        while (true) {
            try {
                /** @type {(null|?)} */
                const message = this.readBuffer.readMessage();
                if (message === null) {
                    break;
                }
                this.onmessage?.(message);
            }
            catch (error) {
                this.onerror?.(error instanceof Error ? error : new Error(String(error)));
            }
        }
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async close() {
        this.stdin.off('data', this.onData);
        this.stdin.off('error', this.onError);
        if (this.stdin.listenerCount('data') === 0) {
            this.stdin.pause();
        }
        this.readBuffer.clear();
        this.onclose?.();
    }
    /**
     * @public
     * @param {?} message
     * @return {!Promise<void>}
     */
    send(message) {
        return new Promise((/**
         * @param {function((void|!PromiseLike<void>)): void} resolve
         * @return {void}
         */
        (resolve) => {
            /** @type {string} */
            const json = serializeMessage(message);
            if (this.stdout.write(json)) {
                resolve();
            }
            else {
                this.stdout.once('drain', resolve);
            }
        }));
    }
}
exports.StdioServerTransport = StdioServerTransport;
/* istanbul ignore if */
if (false) {
    /**
     * @const {!ReadBuffer}
     * @private
     */
    StdioServerTransport.prototype.readBuffer;
    /**
     * @type {boolean}
     * @private
     */
    StdioServerTransport.prototype.started;
    /**
     * @type {(undefined|function(): void)}
     * @public
     */
    StdioServerTransport.prototype.onclose;
    /**
     * @type {(undefined|function(!Error): void)}
     * @public
     */
    StdioServerTransport.prototype.onerror;
    /**
     * @type {(undefined|function(?): void)}
     * @public
     */
    StdioServerTransport.prototype.onmessage;
    /**
     * @const {function(?): void}
     * @private
     */
    StdioServerTransport.prototype.onData;
    /**
     * @const {function(!Error): void}
     * @private
     */
    StdioServerTransport.prototype.onError;
    /**
     * @const {!NodeJS.ReadStream}
     * @private
     */
    StdioServerTransport.prototype.stdin;
    /**
     * @const {!NodeJS.WriteStream}
     * @private
     */
    StdioServerTransport.prototype.stdout;
}
/**
 * Parameters for spawning an MCP server subprocess over stdio.
 * @record
 */
function StdioServerParameters() { }
exports.StdioServerParameters = StdioServerParameters;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    StdioServerParameters.prototype.command;
    /**
     * @type {(undefined|!Array<string>)}
     * @public
     */
    StdioServerParameters.prototype.args;
    /**
     * @type {(undefined|?)}
     * @public
     */
    StdioServerParameters.prototype.env;
    /**
     * @type {(undefined|string)}
     * @public
     */
    StdioServerParameters.prototype.stderr;
    /**
     * @type {(undefined|string)}
     * @public
     */
    StdioServerParameters.prototype.cwd;
}
/** @type {!Array<string>} */
const DEFAULT_INHERITED_ENV_VARS = process.platform === 'win32'
    ? [
        'APPDATA',
        'HOMEDRIVE',
        'HOMEPATH',
        'LOCALAPPDATA',
        'PATH',
        'PROCESSOR_ARCHITECTURE',
        'SYSTEMDRIVE',
        'SYSTEMROOT',
        'TEMP',
        'USERNAME',
        'USERPROFILE',
        'PROGRAMFILES',
    ]
    : ['HOME', 'LOGNAME', 'PATH', 'SHELL', 'TERM', 'USER'];
/**
 * @return {?}
 */
function getDefaultEnvironment() {
    /** @type {?} */
    const env = {};
    for (const key of DEFAULT_INHERITED_ENV_VARS) {
        /** @type {(undefined|string)} */
        const value = process.env[key];
        if (value === undefined || value.startsWith('()')) {
            continue;
        }
        env[key] = value;
    }
    return env;
}
/**
 * Client transport for stdio: connects to a subprocess MCP server over its
 * stdin/stdout streams.
 * @implements {tsickle_transport_1.Transport}
 */
class StdioClientTransport {
    /**
     * @public
     * @param {!StdioServerParameters} serverParams
     */
    constructor(serverParams) {
        this.serverParams = serverParams;
        this.readBuffer = new ReadBuffer();
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async start() {
        if (this.childProcess) {
            throw new Error('StdioClientTransport already started! If using Client class, note that connect() calls start() automatically.');
        }
        return new Promise((/**
         * @param {function((void|!PromiseLike<void>)): void} resolve
         * @param {function(?=): void} reject
         * @return {void}
         */
        (resolve, reject) => {
            /** @type {!tsickle_child_process_3.ChildProcess} */
            const child = (0, child_process_1.spawn)(this.serverParams.command, this.serverParams.args ?? [], {
                env: {
                    ...getDefaultEnvironment(),
                    ...this.serverParams.env,
                },
                stdio: ['pipe', 'pipe', this.serverParams.stderr ?? 'inherit'],
                shell: false,
                windowsHide: process.platform === 'win32',
                cwd: this.serverParams.cwd,
            });
            this.childProcess = child;
            child.on('error', (/**
             * @param {!Error} error
             * @return {void}
             */
            (error) => {
                reject(error);
                this.onerror?.(error);
            }));
            child.on('spawn', (/**
             * @return {void}
             */
            () => {
                resolve();
            }));
            child.on('close', (/**
             * @return {void}
             */
            () => {
                this.childProcess = undefined;
                this.onclose?.();
            }));
            child.stdin?.on('error', (/**
             * @param {!Error} error
             * @return {void}
             */
            (error) => {
                this.onerror?.(error);
            }));
            child.stdout?.on('data', (/**
             * @param {?} chunk
             * @return {void}
             */
            (chunk) => {
                this.readBuffer.append(chunk);
                this.processReadBuffer();
            }));
            child.stdout?.on('error', (/**
             * @param {!Error} error
             * @return {void}
             */
            (error) => {
                this.onerror?.(error);
            }));
        }));
    }
    /**
     * @private
     * @return {void}
     */
    processReadBuffer() {
        while (true) {
            try {
                /** @type {(null|?)} */
                const message = this.readBuffer.readMessage();
                if (message === null) {
                    break;
                }
                this.onmessage?.(message);
            }
            catch (error) {
                this.onerror?.(error instanceof Error ? error : new Error(String(error)));
            }
        }
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async close() {
        this.childProcess?.kill();
        this.childProcess = undefined;
        this.readBuffer.clear();
    }
    /**
     * @public
     * @param {?} message
     * @return {!Promise<void>}
     */
    send(message) {
        return new Promise((/**
         * @param {function((void|!PromiseLike<void>)): void} resolve
         * @param {function(?=): void} reject
         * @return {void}
         */
        (resolve, reject) => {
            if (!this.childProcess?.stdin) {
                reject(new Error('Not connected'));
                return;
            }
            /** @type {string} */
            const json = serializeMessage(message);
            if (this.childProcess.stdin.write(json)) {
                resolve();
            }
            else {
                this.childProcess.stdin.once('drain', resolve);
            }
        }));
    }
}
exports.StdioClientTransport = StdioClientTransport;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|!tsickle_child_process_3.ChildProcess)}
     * @private
     */
    StdioClientTransport.prototype.childProcess;
    /**
     * @const {!ReadBuffer}
     * @private
     */
    StdioClientTransport.prototype.readBuffer;
    /**
     * @type {(undefined|function(): void)}
     * @public
     */
    StdioClientTransport.prototype.onclose;
    /**
     * @type {(undefined|function(!Error): void)}
     * @public
     */
    StdioClientTransport.prototype.onerror;
    /**
     * @type {(undefined|function(?): void)}
     * @public
     */
    StdioClientTransport.prototype.onmessage;
    /**
     * @const {!StdioServerParameters}
     * @private
     */
    StdioClientTransport.prototype.serverParams;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview Shared Jupyter notebook JSON types and helpers for standalone CLI MCP tools.
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/notebook_types.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/notebook_types.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/**
 * Raw Jupyter notebook cell output structure.
 * @record
 */
function NotebookOutputJson() { }
exports.NotebookOutputJson = NotebookOutputJson;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|string)}
     * @public
     */
    NotebookOutputJson.prototype.output_type;
    /**
     * @type {(undefined|string)}
     * @public
     */
    NotebookOutputJson.prototype.name;
    /**
     * @type {(undefined|string|!Array<string>)}
     * @public
     */
    NotebookOutputJson.prototype.text;
    /**
     * @type {(undefined|?)}
     * @public
     */
    NotebookOutputJson.prototype.data;
    /**
     * @type {(undefined|string|!Array<string>)}
     * @public
     */
    NotebookOutputJson.prototype.traceback;
}
/**
 * Raw Jupyter notebook cell structure.
 * @record
 */
function NotebookCellJson() { }
exports.NotebookCellJson = NotebookCellJson;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    NotebookCellJson.prototype.cell_type;
    /**
     * @type {(undefined|?)}
     * @public
     */
    NotebookCellJson.prototype.metadata;
    /**
     * @type {(undefined|string|!Array<string>)}
     * @public
     */
    NotebookCellJson.prototype.source;
    /**
     * @type {(undefined|!Array<!NotebookOutputJson>)}
     * @public
     */
    NotebookCellJson.prototype.outputs;
    /**
     * @type {(undefined|null|number)}
     * @public
     */
    NotebookCellJson.prototype.execution_count;
}
/**
 * Raw Jupyter notebook document structure with validated cells array.
 * @record
 */
function NotebookJson() { }
exports.NotebookJson = NotebookJson;
/* istanbul ignore if */
if (false) {
    /**
     * @type {!Array<!NotebookCellJson>}
     * @public
     */
    NotebookJson.prototype.cells;
    /**
     * @type {(undefined|?)}
     * @public
     */
    NotebookJson.prototype.metadata;
    /**
     * @type {(undefined|number)}
     * @public
     */
    NotebookJson.prototype.nbformat;
    /**
     * @type {(undefined|number)}
     * @public
     */
    NotebookJson.prototype.nbformat_minor;
}
// tslint:enable:enforce-name-casing
/**
 * @param {*} value
 * @return {boolean}
 */
function isNotebookJson(value) {
    return (typeof value === 'object' &&
        value !== null &&
        'cells' in value &&
        Array.isArray(value.cells));
}
/**
 * Parses a notebook JSON string and validates that it has a `cells` array.
 * @param {string} data
 * @return {!NotebookJson}
 */
function parseNotebookJson(data) {
    /** @type {*} */
    const parsed = JSON.parse(data);
    if (!isNotebookJson(parsed)) {
        throw new Error('Invalid notebook format: missing cells array');
    }
    return parsed;
}
exports.parseNotebookJson = parseNotebookJson;
/**
 * Extracts the error message from an unknown caught value.
 * @param {*} error
 * @return {string}
 */
function getErrorMessage(error) {
    return error instanceof Error ? (/** @type {!Error} */ (error)).message : String(error);
}
exports.getErrorMessage = getErrorMessage;

;return exports;});
goog.loadModule(function(exports) {'use strict';// THIS FILE IS GENERATED, DO NOT MODIFY.
goog.module('google3.third_party.javascript.typings.node.node.fs.promises');
/**
* @type {?}
*/
exports = (/** @type {!function(string): ?} */(
typeof require === 'function' ? require : function(s) { return { }; }
))('fs/promises');

;return exports;});
goog.loadModule(function(exports) {'use strict';// THIS FILE IS GENERATED, DO NOT MODIFY.
goog.module('google3.third_party.javascript.typings.node.node.path');
/**
* @type {?}
*/
exports = (/** @type {!function(string): ?} */(
typeof require === 'function' ? require : function(s) { return { }; }
))('path');

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/create_notebook.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.create_notebook');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/create_notebook.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_path_2 = goog.requireType("google3.third_party.javascript.typings.node.node.path");
const tsickle_notebook_types_3 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const path = goog.require('google3.third_party.javascript.typings.node.node.path');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Result returned when creating a notebook.
 * @record
 */
function CreateNotebookResult() { }
exports.CreateNotebookResult = CreateNotebookResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {boolean}
     * @public
     */
    CreateNotebookResult.prototype.success;
    /**
     * @const {string}
     * @public
     */
    CreateNotebookResult.prototype.message;
    /**
     * @const {string}
     * @public
     */
    CreateNotebookResult.prototype.notebookPath;
}
/**
 * @param {*} err
 * @return {boolean}
 */
function isErrnoException(err) {
    return typeof err === 'object' && err !== null && 'code' in err;
}
/**
 * Creates a new empty Jupyter notebook file in the given directory.
 * @param {string} directory
 * @param {string} filename
 * @return {!Promise<!CreateNotebookResult>}
 */
async function createNotebook(directory, filename) {
    try {
        /** @type {string} */
        const extension = 'ipynb';
        /** @type {string} */
        const fullFilename = filename.endsWith(`.${extension}`)
            ? filename
            : `${filename}.${extension}`;
        /** @type {string} */
        const notebookPath = path.join(directory, fullFilename);
        try {
            await fs.stat(notebookPath);
            throw new Error(`Notebook already exists at ${notebookPath}`);
        }
        catch (err) {
            if (!isErrnoException(err) || (/** @type {!NodeJS.ErrnoException} */ (err)).code !== 'ENOENT') {
                throw err;
            }
        }
        /** @type {!tsickle_notebook_types_3.NotebookJson} */
        const minimalNotebook = {
            cells: [],
            metadata: {},
            nbformat: 4,
            nbformat_minor: 2,
        };
        await fs.writeFile(notebookPath, JSON.stringify(minimalNotebook, null, 2), 'utf8');
        return {
            success: true,
            message: `Created Jupyter notebook at ${notebookPath}`,
            notebookPath,
        };
    }
    catch (error) {
        throw new Error(`Failed to create notebook: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.createNotebook = createNotebook;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/delete_cell.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.delete_cell');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/delete_cell.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Result returned when deleting a notebook cell.
 * @record
 */
function DeleteCellResult() { }
exports.DeleteCellResult = DeleteCellResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {boolean}
     * @public
     */
    DeleteCellResult.prototype.success;
    /**
     * @const {string}
     * @public
     */
    DeleteCellResult.prototype.message;
}
/**
 * Deletes a cell at the given 0-based index from a Jupyter notebook.
 * @param {string} notebookPath
 * @param {number} cellIndex
 * @return {!Promise<!DeleteCellResult>}
 */
async function deleteCell(notebookPath, cellIndex) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        if (cellIndex < 0 || cellIndex >= notebook.cells.length) {
            throw new Error(`Cell index out of bounds: ${cellIndex}. Total cells: ${notebook.cells.length}`);
        }
        notebook.cells.splice(cellIndex, 1);
        await fs.writeFile(notebookPath, JSON.stringify(notebook, null, 2), 'utf8');
        return {
            success: true,
            message: `Cell at index ${cellIndex} deleted`,
        };
    }
    catch (error) {
        throw new Error(`Failed to delete cell: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.deleteCell = deleteCell;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/get_cell_outputs.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_cell_outputs');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/get_cell_outputs.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Content items returned for cell execution outputs.
 * @typedef {!Array<({type: string, text: string}|{type: string, data: string, mimeType: string})>}
 */
exports.McpContentPayload;
/**
 * Reads execution outputs from a code cell by 0-based index.
 * @param {string} notebookPath
 * @param {number} cellIndex
 * @return {!Promise<!Array<({type: string, text: string}|{type: string, data: string, mimeType: string})>>}
 */
async function getCellOutputs(notebookPath, cellIndex) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        if (cellIndex < 0 || cellIndex >= notebook.cells.length) {
            throw new Error(`Cell index out of bounds: ${cellIndex}. Total cells: ${notebook.cells.length}`);
        }
        /** @type {!tsickle_notebook_types_2.NotebookCellJson} */
        const cell = notebook.cells[cellIndex];
        if (cell.cell_type !== 'code') {
            throw new Error(`Cell at index ${cellIndex} is not a code cell; it has no execution outputs.`);
        }
        /** @type {string} */
        const prefixText = `Outputs for cell ${cellIndex} in ${notebookPath}:`;
        return parseCellOutputs(cell, prefixText);
    }
    catch (error) {
        throw new Error(`Failed to get cell outputs: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.getCellOutputs = getCellOutputs;
/**
 * @param {!tsickle_notebook_types_2.NotebookCellJson} cell
 * @param {string} prefixText
 * @return {!Array<({type: string, text: string}|{type: string, data: string, mimeType: string})>}
 */
function parseCellOutputs(cell, prefixText) {
    /** @type {!Array<({type: string, text: string}|{type: string, data: string, mimeType: string})>} */
    const contentPayload = [];
    /** @type {string} */
    let textBuffer = `${prefixText}\n`;
    /** @type {(null|number)} */
    const executionCount = cell.execution_count ?? null;
    textBuffer += `Execution Count: ${executionCount ?? 'N/A'}\n`;
    if (cell.outputs && cell.outputs.length > 0) {
        textBuffer += '\nOutputs:\n';
        for (const o of cell.outputs) {
            /** @type {(undefined|string)} */
            const outputType = o.output_type;
            if (outputType === 'stream') {
                /** @type {string} */
                const text = Array.isArray(o.text) ? (/** @type {!Array<string>} */ (o.text)).join('') : (o.text ?? '');
                /** @type {string} */
                const textPreview = text.length > 3000 ? `${text.slice(0, 3000)}\n...[Truncated]` : text;
                textBuffer += `\n[stream:${o.name ?? ''}]\n${textPreview}\n`;
            }
            else if (outputType === 'execute_result' ||
                outputType === 'display_data') {
                /** @type {?} */
                const outputData = o.data ?? {};
                for (const [mime__tsickle_destructured_1, rawData__tsickle_destructured_2] of Object.entries(outputData)) {
                    const mime = /** @type {string} */ (mime__tsickle_destructured_1);
                    const rawData = /** @type {*} */ (rawData__tsickle_destructured_2);
                    /** @type {?} */
                    const textData = Array.isArray(rawData)
                        ? (/** @type {!Array<?>} */ (rawData)).join('')
                        : (rawData ?? '');
                    if (mime.startsWith('text/') || mime.includes('json')) {
                        /** @type {string} */
                        const strData = String(textData);
                        /** @type {string} */
                        const textPreview = strData.length > 3000
                            ? `${strData.slice(0, 3000)}\n...[Truncated]`
                            : strData;
                        textBuffer += `\n[${mime}]\n${textPreview}\n`;
                    }
                    else if (mime === 'image/png' || mime === 'image/jpeg') {
                        if (textBuffer.trim().length > 0) {
                            contentPayload.push({ type: 'text', text: textBuffer });
                            textBuffer = '';
                        }
                        if (typeof textData !== 'string') {
                            textBuffer += `\n[${mime}]\n(Warning: Image data is not a string. Type: ${typeof textData})\n`;
                        }
                        else {
                            contentPayload.push({
                                type: 'image',
                                data: textData,
                                mimeType: mime,
                            });
                        }
                    }
                }
            }
            else if (outputType === 'error') {
                /** @type {string} */
                const traceback = Array.isArray(o.traceback)
                    ? (/** @type {!Array<string>} */ (o.traceback)).join('\n')
                    : (o.traceback ?? '');
                textBuffer += `\n[error]\n${traceback}\n`;
            }
        }
    }
    else {
        textBuffer += '\n(No output generated)\n';
    }
    if (textBuffer.length > 0) {
        contentPayload.push({ type: 'text', text: textBuffer });
    }
    return contentPayload;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/get_notebook_info.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_notebook_info');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/get_notebook_info.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Summary information about a Jupyter notebook.
 * @record
 */
function NotebookInfoResult() { }
exports.NotebookInfoResult = NotebookInfoResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {number}
     * @public
     */
    NotebookInfoResult.prototype.totalCells;
    /**
     * @const {{code: number, markdown: number}}
     * @public
     */
    NotebookInfoResult.prototype.cellTypeSummary;
    /**
     * @const {?}
     * @public
     */
    NotebookInfoResult.prototype.metadata;
}
/**
 * Returns summary cell count and metadata information for a Jupyter notebook.
 * @param {string} notebookPath
 * @return {!Promise<!NotebookInfoResult>}
 */
async function getNotebookInfo(notebookPath) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        /** @type {number} */
        const totalCells = notebook.cells.length;
        /** @type {number} */
        let codeCells = 0;
        /** @type {number} */
        let markdownCells = 0;
        for (const cell of notebook.cells) {
            if (cell.cell_type === 'code') {
                codeCells++;
            }
            if (cell.cell_type === 'markdown') {
                markdownCells++;
            }
        }
        return {
            totalCells,
            cellTypeSummary: {
                code: codeCells,
                markdown: markdownCells,
            },
            metadata: notebook.metadata ?? {},
        };
    }
    catch (error) {
        throw new Error(`Failed to get notebook info: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.getNotebookInfo = getNotebookInfo;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/insert_cell.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.insert_cell');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/insert_cell.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Result returned when inserting a notebook cell.
 * @record
 */
function InsertCellResult() { }
exports.InsertCellResult = InsertCellResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {boolean}
     * @public
     */
    InsertCellResult.prototype.success;
    /**
     * @const {string}
     * @public
     */
    InsertCellResult.prototype.message;
}
/**
 * Inserts a new code or markdown cell into a Jupyter notebook.
 * @param {string} notebookPath
 * @param {string} cellType
 * @param {string} content
 * @param {(undefined|number)=} cellIndex
 * @return {!Promise<!InsertCellResult>}
 */
async function insertCell(notebookPath, cellType, content, cellIndex) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        /** @type {!tsickle_notebook_types_2.NotebookCellJson} */
        const newCell = cellType === 'code'
            ? {
                cell_type: cellType,
                metadata: {},
                source: [content],
                outputs: [],
                execution_count: null,
            }
            : {
                cell_type: cellType,
                metadata: {},
                source: [content],
            };
        if (cellIndex === undefined || cellIndex >= notebook.cells.length) {
            notebook.cells.push(newCell);
        }
        else if (cellIndex < 0) {
            notebook.cells.unshift(newCell);
        }
        else {
            notebook.cells.splice(cellIndex, 0, newCell);
        }
        await fs.writeFile(notebookPath, JSON.stringify(notebook, null, 2), 'utf8');
        return {
            success: true,
            message: `Cell inserted at index ${cellIndex !== undefined ? cellIndex : notebook.cells.length - 1}`,
        };
    }
    catch (error) {
        throw new Error(`Failed to insert cell: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.insertCell = insertCell;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/list_cells.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.list_cells');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/list_cells.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Summary entry for a single notebook cell.
 * @record
 */
function CellListItem() { }
exports.CellListItem = CellListItem;
/* istanbul ignore if */
if (false) {
    /**
     * @const {number}
     * @public
     */
    CellListItem.prototype.index;
    /**
     * @const {string}
     * @public
     */
    CellListItem.prototype.type;
    /**
     * @const {string}
     * @public
     */
    CellListItem.prototype.preview;
}
/**
 * Result returned when listing notebook cells.
 * @record
 */
function ListCellsResult() { }
exports.ListCellsResult = ListCellsResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {!Array<!CellListItem>}
     * @public
     */
    ListCellsResult.prototype.cells;
}
/**
 * Lists all cells in a Jupyter notebook with preview snippets.
 * @param {string} notebookPath
 * @param {number=} maxLength
 * @return {!Promise<!ListCellsResult>}
 */
async function listCells(notebookPath, maxLength = 100) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        /** @type {!Array<!CellListItem>} */
        const cells = notebook.cells.map((/**
         * @param {!tsickle_notebook_types_2.NotebookCellJson} cell
         * @param {number} index
         * @return {{index: number, type: string, preview: string}}
         */
        (cell, index) => {
            /** @type {string} */
            const source = Array.isArray(cell.source)
                ? (/** @type {!Array<string>} */ (cell.source)).join('')
                : (cell.source ?? '');
            /** @type {string} */
            const fullPreview = source.split('\n')[0] ?? '';
            /** @type {boolean} */
            const needsTruncation = fullPreview.length > maxLength;
            /** @type {string} */
            const previewText = needsTruncation
                ? `${fullPreview.substring(0, maxLength)}... [truncated]`
                : fullPreview;
            return {
                index,
                type: cell.cell_type,
                preview: previewText,
            };
        }));
        return {
            cells,
        };
    }
    catch (error) {
        throw new Error(`Failed to list cells: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.listCells = listCells;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/read_cell.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.read_cell');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/read_cell.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Result returned when reading a notebook cell.
 * @record
 */
function ReadCellResult() { }
exports.ReadCellResult = ReadCellResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {string}
     * @public
     */
    ReadCellResult.prototype.cellType;
    /**
     * @const {string}
     * @public
     */
    ReadCellResult.prototype.content;
    /**
     * @const {!Array<!tsickle_notebook_types_2.NotebookOutputJson>}
     * @public
     */
    ReadCellResult.prototype.outputs;
}
/**
 * Reads the content and outputs of a cell at a given 0-based index.
 * @param {string} notebookPath
 * @param {number} cellIndex
 * @return {!Promise<!ReadCellResult>}
 */
async function readCell(notebookPath, cellIndex) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        if (cellIndex < 0 || cellIndex >= notebook.cells.length) {
            throw new Error(`Cell index out of bounds: ${cellIndex}. Total cells: ${notebook.cells.length}`);
        }
        /** @type {!tsickle_notebook_types_2.NotebookCellJson} */
        const cell = notebook.cells[cellIndex];
        /** @type {string} */
        const source = Array.isArray(cell.source)
            ? (/** @type {!Array<string>} */ (cell.source)).join('')
            : (cell.source ?? '');
        /** @type {!Array<!tsickle_notebook_types_2.NotebookOutputJson>} */
        const outputs = cell.outputs ?? [];
        return {
            cellType: cell.cell_type,
            content: source,
            outputs,
        };
    }
    catch (error) {
        throw new Error(`Failed to read cell: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.readCell = readCell;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/replace_cell.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.replace_cell');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/replace_cell.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Result returned when replacing a notebook cell.
 * @record
 */
function ReplaceCellResult() { }
exports.ReplaceCellResult = ReplaceCellResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {boolean}
     * @public
     */
    ReplaceCellResult.prototype.success;
    /**
     * @const {string}
     * @public
     */
    ReplaceCellResult.prototype.message;
}
/**
 * Replaces the content of a specific cell in a Jupyter notebook.
 * @param {string} notebookPath
 * @param {number} cellIndex
 * @param {string} content
 * @return {!Promise<!ReplaceCellResult>}
 */
async function replaceCell(notebookPath, cellIndex, content) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        if (cellIndex < 0 || cellIndex >= notebook.cells.length) {
            throw new Error(`Cell index out of bounds: ${cellIndex}. Total cells: ${notebook.cells.length}`);
        }
        notebook.cells[cellIndex].source = [content];
        await fs.writeFile(notebookPath, JSON.stringify(notebook, null, 2), 'utf8');
        return {
            success: true,
            message: `Cell at index ${cellIndex} replaced`,
        };
    }
    catch (error) {
        throw new Error(`Failed to replace cell: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.replaceCell = replaceCell;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/search_cells.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.search_cells');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/tools/search_cells.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_promises_1 = goog.requireType("google3.third_party.javascript.typings.node.node.fs.promises");
const tsickle_notebook_types_2 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types");
const fs = goog.require('google3.third_party.javascript.typings.node.node.fs.promises');
const notebook_types_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.notebook_types');
/**
 * Search match entry for a notebook cell.
 * @record
 */
function CellSearchMatch() { }
exports.CellSearchMatch = CellSearchMatch;
/* istanbul ignore if */
if (false) {
    /**
     * @const {number}
     * @public
     */
    CellSearchMatch.prototype.cell_index;
    /**
     * @const {string}
     * @public
     */
    CellSearchMatch.prototype.type;
    /**
     * @const {!Array<string>}
     * @public
     */
    CellSearchMatch.prototype.matches;
}
/**
 * Result returned when searching notebook cells.
 * @record
 */
function SearchCellsResult() { }
exports.SearchCellsResult = SearchCellsResult;
/* istanbul ignore if */
if (false) {
    /**
     * @const {!Array<!CellSearchMatch>}
     * @public
     */
    SearchCellsResult.prototype.matches;
}
/**
 * Searches for text within cells of a Jupyter notebook.
 * @param {string} notebookPath
 * @param {string} query
 * @param {boolean=} caseSensitive
 * @return {!Promise<!SearchCellsResult>}
 */
async function searchCells(notebookPath, query, caseSensitive = false) {
    try {
        /** @type {string} */
        const data = await fs.readFile(notebookPath, 'utf8');
        /** @type {!tsickle_notebook_types_2.NotebookJson} */
        const notebook = (0, notebook_types_1.parseNotebookJson)(data);
        /** @type {!Array<!CellSearchMatch>} */
        const matches = [];
        /** @type {string} */
        const searchFor = caseSensitive ? query : query.toLowerCase();
        notebook.cells.forEach((/**
         * @param {!tsickle_notebook_types_2.NotebookCellJson} cell
         * @param {number} index
         * @return {void}
         */
        (cell, index) => {
            /** @type {string} */
            const source = Array.isArray(cell.source)
                ? (/** @type {!Array<string>} */ (cell.source)).join('')
                : (cell.source ?? '');
            /** @type {!Array<string>} */
            const lines = source.split('\n');
            /** @type {!Array<string>} */
            const matchingLines = lines.filter((/**
             * @param {string} line
             * @return {boolean}
             */
            (line) => {
                /** @type {string} */
                const textToSearch = caseSensitive ? line : line.toLowerCase();
                return textToSearch.includes(searchFor);
            }));
            if (matchingLines.length > 0) {
                matches.push({
                    cell_index: index,
                    type: cell.cell_type,
                    matches: matchingLines,
                });
            }
        }));
        return {
            matches,
        };
    }
    catch (error) {
        throw new Error(`Failed to search cells: ${(0, notebook_types_1.getErrorMessage)(error)}`);
    }
}
exports.searchCells = searchCells;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/deep-compare-strict.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.deep$2dcompare$2dstrict');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/deep-compare-strict.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/**
 * @param {?} a
 * @param {?} b
 * @return {boolean}
 */
function deepCompareStrict(a, b) {
    /** @type {string} */
    const typeofa = typeof a;
    if (typeofa !== typeof b) {
        return false;
    }
    if (Array.isArray(a)) {
        if (!Array.isArray(b)) {
            return false;
        }
        /** @type {number} */
        const length = (/** @type {!Array<?>} */ (a)).length;
        if (length !== (/** @type {!Array<?>} */ (b)).length) {
            return false;
        }
        for (let i = 0; i < length; i++) {
            if (!deepCompareStrict(a[i], b[i])) {
                return false;
            }
        }
        return true;
    }
    if (typeofa === 'object') {
        if (!a || !b) {
            return a === b;
        }
        /** @type {!Array<string>} */
        const aKeys = Object.keys(a);
        /** @type {!Array<string>} */
        const bKeys = Object.keys(b);
        /** @type {number} */
        const length = aKeys.length;
        if (length !== bKeys.length) {
            return false;
        }
        for (const k of aKeys) {
            if (!deepCompareStrict(a[k], b[k])) {
                return false;
            }
        }
        return true;
    }
    return a === b;
}
exports.deepCompareStrict = deepCompareStrict;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/pointer.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.pointer');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/pointer.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/**
 * @param {string} p
 * @return {string}
 */
function encodePointer(p) {
    return encodeURI(escapePointer(p));
}
exports.encodePointer = encodePointer;
/**
 * @param {string} p
 * @return {string}
 */
function escapePointer(p) {
    return p.replace(/~/g, '~0').replace(/\//g, '~1');
}
exports.escapePointer = escapePointer;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/dereference.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.dereference');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/dereference.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_pointer_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.pointer");
const tsickle_types_2 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.types");
const pointer_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.pointer');
/** @type {?} */
exports.schemaKeyword = {
    additionalItems: true,
    unevaluatedItems: true,
    items: true,
    contains: true,
    additionalProperties: true,
    unevaluatedProperties: true,
    propertyNames: true,
    not: true,
    if: true,
    then: true,
    else: true
};
/** @type {?} */
exports.schemaArrayKeyword = {
    prefixItems: true,
    items: true,
    allOf: true,
    anyOf: true,
    oneOf: true
};
/** @type {?} */
exports.schemaMapKeyword = {
    $defs: true,
    definitions: true,
    properties: true,
    patternProperties: true,
    dependentSchemas: true
};
/** @type {?} */
exports.ignoredKeyword = {
    id: true,
    $id: true,
    $ref: true,
    $schema: true,
    $anchor: true,
    $vocabulary: true,
    $comment: true,
    default: true,
    enum: true,
    const: true,
    required: true,
    type: true,
    maximum: true,
    minimum: true,
    exclusiveMaximum: true,
    exclusiveMinimum: true,
    multipleOf: true,
    maxLength: true,
    minLength: true,
    pattern: true,
    format: true,
    maxItems: true,
    minItems: true,
    uniqueItems: true,
    maxProperties: true,
    minProperties: true
};
/**
 * Default base URI for schemas without an $id.
 * https://json-schema.org/draft/2019-09/json-schema-core.html#initial-base
 * https://tools.ietf.org/html/rfc3986#section-5.1
 * @type {!URL}
 */
exports.initialBaseURI = 
// @ts-ignore
typeof self !== 'undefined' && self.location
    ? //@ts-ignore
        new URL(self.location.origin + self.location.pathname + location.search)
    : new URL('https://github.com/cfworker');
/**
 * @param {(boolean|!tsickle_types_2.Schema)} schema
 * @param {?=} lookup
 * @param {!URL=} baseURI
 * @param {string=} basePointer
 * @return {?}
 */
function dereference(schema, lookup = Object.create(null), baseURI = exports.initialBaseURI, basePointer = '') {
    if (schema && typeof schema === 'object' && !Array.isArray(schema)) {
        /** @type {string} */
        const id = (/** @type {!tsickle_types_2.Schema} */ (schema)).$id || (/** @type {!tsickle_types_2.Schema} */ (schema)).id;
        if (id) {
            /** @type {!URL} */
            const url = new URL(id, baseURI.href);
            if (url.hash.length > 1) {
                lookup[url.href] = schema;
            }
            else {
                url.hash = ''; // normalize hash https://url.spec.whatwg.org/#dom-url-hash
                if (basePointer === '') {
                    baseURI = url;
                }
                else {
                    dereference(schema, lookup, baseURI);
                }
            }
        }
    }
    else if (schema !== true && schema !== false) {
        return lookup;
    }
    // compute the schema's URI and add it to the mapping.
    /** @type {string} */
    const schemaURI = baseURI.href + (basePointer ? '#' + basePointer : '');
    if (lookup[schemaURI] !== undefined) {
        throw new Error(`Duplicate schema URI "${schemaURI}".`);
    }
    lookup[schemaURI] = schema;
    // exit early if this is a boolean schema.
    if (schema === true || schema === false) {
        return lookup;
    }
    // set the schema's absolute URI.
    if ((/** @type {!tsickle_types_2.Schema} */ (schema)).__absolute_uri__ === undefined) {
        Object.defineProperty(schema, '__absolute_uri__', {
            enumerable: false,
            value: schemaURI
        });
    }
    // if a $ref is found, resolve it's absolute URI.
    if ((/** @type {!tsickle_types_2.Schema} */ (schema)).$ref && (/** @type {!tsickle_types_2.Schema} */ (schema)).__absolute_ref__ === undefined) {
        /** @type {!URL} */
        const url = new URL((/** @type {!tsickle_types_2.Schema} */ (schema)).$ref, baseURI.href);
        url.hash = url.hash; // normalize hash https://url.spec.whatwg.org/#dom-url-hash
        // normalize hash https://url.spec.whatwg.org/#dom-url-hash
        Object.defineProperty(schema, '__absolute_ref__', {
            enumerable: false,
            value: url.href
        });
    }
    // if a $recursiveRef is found, resolve it's absolute URI.
    if ((/** @type {!tsickle_types_2.Schema} */ (schema)).$recursiveRef && (/** @type {!tsickle_types_2.Schema} */ (schema)).__absolute_recursive_ref__ === undefined) {
        /** @type {!URL} */
        const url = new URL((/** @type {!tsickle_types_2.Schema} */ (schema)).$recursiveRef, baseURI.href);
        url.hash = url.hash; // normalize hash https://url.spec.whatwg.org/#dom-url-hash
        // normalize hash https://url.spec.whatwg.org/#dom-url-hash
        Object.defineProperty(schema, '__absolute_recursive_ref__', {
            enumerable: false,
            value: url.href
        });
    }
    // if an $anchor is found, compute it's URI and add it to the mapping.
    if ((/** @type {!tsickle_types_2.Schema} */ (schema)).$anchor) {
        /** @type {!URL} */
        const url = new URL('#' + (/** @type {!tsickle_types_2.Schema} */ (schema)).$anchor, baseURI.href);
        lookup[url.href] = schema;
    }
    // process subschemas.
    for (let key in schema) {
        if (exports.ignoredKeyword[key]) {
            continue;
        }
        /** @type {string} */
        const keyBase = `${basePointer}/${(0, pointer_js_1.encodePointer)(key)}`;
        /** @type {?} */
        const subSchema = schema[key];
        if (Array.isArray(subSchema)) {
            if (exports.schemaArrayKeyword[key]) {
                /** @type {number} */
                const length = (/** @type {!Array<?>} */ (subSchema)).length;
                for (let i = 0; i < length; i++) {
                    dereference(subSchema[i], lookup, baseURI, `${keyBase}/${i}`);
                }
            }
        }
        else if (exports.schemaMapKeyword[key]) {
            for (let subKey in subSchema) {
                dereference(subSchema[subKey], lookup, baseURI, `${keyBase}/${(0, pointer_js_1.encodePointer)(subKey)}`);
            }
        }
        else {
            dereference(subSchema, lookup, baseURI, keyBase);
        }
    }
    return lookup;
}
exports.dereference = dereference;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
// based on https://github.com/epoberezkin/ajv/blob/master/lib/compile/formats.js
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/format.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.format');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/format.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/** @type {!RegExp} */
const DATE = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
/** @type {!Array<number>} */
const DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
/** @type {!RegExp} */
const TIME = /^(\d\d):(\d\d):(\d\d)(\.\d+)?(z|[+-]\d\d(?::?\d\d)?)?$/i;
/** @type {!RegExp} */
const HOSTNAME = /^(?=.{1,253}\.?$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[-0-9a-z]{0,61}[0-9a-z])?)*\.?$/i;
// const URI = /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)(?:\?(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i;
/** @type {!RegExp} */
const URIREF = /^(?:[a-z][a-z0-9+\-.]*:)?(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'"()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?(?:\?(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i;
// uri-template: https://tools.ietf.org/html/rfc6570
/** @type {!RegExp} */
const URITEMPLATE = /^(?:(?:[^\x00-\x20"'<>%\\^`{|}]|%[0-9a-f]{2})|\{[+#./;?&=,!@|]?(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?(?:,(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?)*\})*$/i;
// For the source: https://gist.github.com/dperini/729294
// For test cases: https://mathiasbynens.be/demo/url-regex
/** @type {!RegExp} */
const URL_ = /^(?:(?:https?|ftp):\/\/)(?:\S+(?::\S*)?@)?(?:(?!10(?:\.\d{1,3}){3})(?!127(?:\.\d{1,3}){3})(?!169\.254(?:\.\d{1,3}){2})(?!192\.168(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u{00a1}-\u{ffff}0-9]+-?)*[a-z\u{00a1}-\u{ffff}0-9]+)(?:\.(?:[a-z\u{00a1}-\u{ffff}0-9]+-?)*[a-z\u{00a1}-\u{ffff}0-9]+)*(?:\.(?:[a-z\u{00a1}-\u{ffff}]{2,})))(?::\d{2,5})?(?:\/[^\s]*)?$/iu;
/** @type {!RegExp} */
const UUID = /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
/** @type {!RegExp} */
const JSON_POINTER = /^(?:\/(?:[^~/]|~0|~1)*)*$/;
/** @type {!RegExp} */
const JSON_POINTER_URI_FRAGMENT = /^#(?:\/(?:[a-z0-9_\-.!$&'()*+,;:=@]|%[0-9a-f]{2}|~0|~1)*)*$/i;
/** @type {!RegExp} */
const RELATIVE_JSON_POINTER = /^(?:0|[1-9][0-9]*)(?:#|(?:\/(?:[^~/]|~0|~1)*)*)$/;
// date: http://tools.ietf.org/html/rfc3339#section-5.6
/** @type {!RegExp} */
const FASTDATE = /^\d\d\d\d-[0-1]\d-[0-3]\d$/;
// date-time: http://tools.ietf.org/html/rfc3339#section-5.6
/** @type {!RegExp} */
const FASTTIME = /^(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)?$/i;
/** @type {!RegExp} */
const FASTDATETIME = /^\d\d\d\d-[0-1]\d-[0-3]\d[t\s](?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)$/i;
// uri: https://github.com/mafintosh/is-my-json-valid/blob/master/formats.js
// const FASTURI = /^(?:[a-z][a-z0-9+-.]*:)(?:\/?\/)?[^\s]*$/i;
/** @type {!RegExp} */
const FASTURIREFERENCE = /^(?:(?:[a-z][a-z0-9+-.]*:)?\/?\/)?(?:[^\\\s#][^\s#]*)?(?:#[^\\\s]*)?$/i;
// https://github.com/ExodusMovement/schemasafe/blob/master/src/formats.js
/** @type {function(string): boolean} */
const EMAIL = (/**
 * @param {string} input
 * @return {boolean}
 */
(input) => {
    if (input[0] === '"')
        return false;
    const [name__tsickle_destructured_1, host__tsickle_destructured_2, ...rest__tsickle_destructured_3] = input.split('@');
    const name = /** @type {string} */ (name__tsickle_destructured_1);
    const host = /** @type {string} */ (host__tsickle_destructured_2);
    const rest = /** @type {!Array<string>} */ (rest__tsickle_destructured_3);
    if (!name ||
        !host ||
        rest.length !== 0 ||
        name.length > 64 ||
        host.length > 253)
        return false;
    if (name[0] === '.' || name.endsWith('.') || name.includes('..'))
        return false;
    if (!/^[a-z0-9.-]+$/i.test(host) ||
        !/^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+$/i.test(name))
        return false;
    return host
        .split('.')
        .every((/**
     * @param {string} part
     * @return {boolean}
     */
    part => /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/i.test(part)));
});
// optimized https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html
/** @type {!RegExp} */
const IPV4 = /^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$/;
// optimized http://stackoverflow.com/questions/53497/regular-expression-that-matches-valid-ipv6-addresses
/** @type {!RegExp} */
const IPV6 = /^((([0-9a-f]{1,4}:){7}([0-9a-f]{1,4}|:))|(([0-9a-f]{1,4}:){6}(:[0-9a-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){5}(((:[0-9a-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){4}(((:[0-9a-f]{1,4}){1,3})|((:[0-9a-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){3}(((:[0-9a-f]{1,4}){1,4})|((:[0-9a-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){2}(((:[0-9a-f]{1,4}){1,5})|((:[0-9a-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){1}(((:[0-9a-f]{1,4}){1,6})|((:[0-9a-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9a-f]{1,4}){1,7})|((:[0-9a-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))$/i;
// https://github.com/ExodusMovement/schemasafe/blob/master/src/formats.js
/** @type {function(string): boolean} */
const DURATION = (/**
 * @param {string} input
 * @return {boolean}
 */
(input) => input.length > 1 &&
    input.length < 80 &&
    (/^P\d+([.,]\d+)?W$/.test(input) ||
        (/^P[\dYMDTHS]*(\d[.,]\d+)?[YMDHS]$/.test(input) &&
            /^P([.,\d]+Y)?([.,\d]+M)?([.,\d]+D)?(T([.,\d]+H)?([.,\d]+M)?([.,\d]+S)?)?$/.test(input))));
/**
 * @param {!RegExp} r
 * @return {?}
 */
function bind(r) {
    return r.test.bind(r);
}
/** @type {?} */
exports.fullFormat = {
    date,
    time: time.bind(undefined, false),
    'date-time': date_time,
    duration: DURATION,
    uri,
    'uri-reference': bind(URIREF),
    'uri-template': bind(URITEMPLATE),
    url: bind(URL_),
    email: EMAIL,
    hostname: bind(HOSTNAME),
    ipv4: bind(IPV4),
    ipv6: bind(IPV6),
    regex: regex,
    uuid: bind(UUID),
    'json-pointer': bind(JSON_POINTER),
    'json-pointer-uri-fragment': bind(JSON_POINTER_URI_FRAGMENT),
    'relative-json-pointer': bind(RELATIVE_JSON_POINTER)
};
/** @type {?} */
exports.fastFormat = {
    ...exports.fullFormat,
    date: bind(FASTDATE),
    time: bind(FASTTIME),
    'date-time': bind(FASTDATETIME),
    'uri-reference': bind(FASTURIREFERENCE)
};
/**
 * @param {number} year
 * @return {boolean}
 */
function isLeapYear(year) {
    // https://tools.ietf.org/html/rfc3339#appendix-C
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}
/**
 * @param {string} str
 * @return {boolean}
 */
function date(str) {
    // full-date from http://tools.ietf.org/html/rfc3339#section-5.6
    /** @type {(null|!RegExpMatchArray)} */
    const matches = str.match(DATE);
    if (!matches)
        return false;
    /** @type {number} */
    const year = +matches[1];
    /** @type {number} */
    const month = +matches[2];
    /** @type {number} */
    const day = +matches[3];
    return (month >= 1 &&
        month <= 12 &&
        day >= 1 &&
        day <= (month == 2 && isLeapYear(year) ? 29 : DAYS[month]));
}
/**
 * @param {boolean} full
 * @param {string} str
 * @return {boolean}
 */
function time(full, str) {
    /** @type {(null|!RegExpMatchArray)} */
    const matches = str.match(TIME);
    if (!matches)
        return false;
    /** @type {number} */
    const hour = +matches[1];
    /** @type {number} */
    const minute = +matches[2];
    /** @type {number} */
    const second = +matches[3];
    /** @type {boolean} */
    const timeZone = !!matches[5];
    return (((hour <= 23 && minute <= 59 && second <= 59) ||
        (hour == 23 && minute == 59 && second == 60)) &&
        (!full || timeZone));
}
/** @type {!RegExp} */
const DATE_TIME_SEPARATOR = /t|\s/i;
/**
 * @param {string} str
 * @return {boolean}
 */
function date_time(str) {
    // http://tools.ietf.org/html/rfc3339#section-5.6
    /** @type {!Array<string>} */
    const dateTime = str.split(DATE_TIME_SEPARATOR);
    return dateTime.length == 2 && date(dateTime[0]) && time(true, dateTime[1]);
}
/** @type {!RegExp} */
const NOT_URI_FRAGMENT = /\/|:/;
/** @type {!RegExp} */
const URI_PATTERN = /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)(?:\?(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i;
/**
 * @param {string} str
 * @return {boolean}
 */
function uri(str) {
    // http://jmrware.com/articles/2009/uri_regexp/URI_regex.html + optional protocol + required "."
    return NOT_URI_FRAGMENT.test(str) && URI_PATTERN.test(str);
}
/** @type {!RegExp} */
const Z_ANCHOR = /[^\\]\\Z/;
/**
 * @param {string} str
 * @return {boolean}
 */
function regex(str) {
    if (Z_ANCHOR.test(str))
        return false;
    try {
        new RegExp(str);
        return true;
    }
    catch (e) {
        return false;
    }
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/types.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.types');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/types.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/** @typedef {string} */
exports.SchemaDraft;
/** @enum {number} */
const OutputFormat = {
    Flag: 1,
    Basic: 2,
    Detailed: 4,
};
exports.OutputFormat = OutputFormat;
/** @typedef {string} */
exports.InstanceType;
/**
 * @record
 */
function Schema() { }
exports.Schema = Schema;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$id;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$anchor;
    /**
     * @type {(undefined|boolean)}
     * @public
     */
    Schema.prototype.$recursiveAnchor;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$ref;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$recursiveRef;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$schema;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.$comment;
    /**
     * @type {?|undefined}
     * @public
     */
    Schema.prototype.$defs;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.$vocabulary;
    /**
     * @type {(undefined|string|!Array<string>)}
     * @public
     */
    Schema.prototype.type;
    /**
     * @type {?|undefined}
     * @public
     */
    Schema.prototype.const;
    /**
     * @type {(undefined|!Array<?>)}
     * @public
     */
    Schema.prototype.enum;
    /**
     * @type {(undefined|!Array<string>)}
     * @public
     */
    Schema.prototype.required;
    /**
     * @type {(undefined|!Schema)}
     * @public
     */
    Schema.prototype.not;
    /**
     * @type {(undefined|!Array<!Schema>)}
     * @public
     */
    Schema.prototype.anyOf;
    /**
     * @type {(undefined|!Array<!Schema>)}
     * @public
     */
    Schema.prototype.allOf;
    /**
     * @type {(undefined|!Array<!Schema>)}
     * @public
     */
    Schema.prototype.oneOf;
    /**
     * @type {(undefined|!Schema)}
     * @public
     */
    Schema.prototype.if;
    /**
     * @type {(undefined|!Schema)}
     * @public
     */
    Schema.prototype.then;
    /**
     * @type {(undefined|!Schema)}
     * @public
     */
    Schema.prototype.else;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.format;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.properties;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.patternProperties;
    /**
     * @type {(undefined|boolean|!Schema)}
     * @public
     */
    Schema.prototype.additionalProperties;
    /**
     * @type {(undefined|boolean|!Schema)}
     * @public
     */
    Schema.prototype.unevaluatedProperties;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.minProperties;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.maxProperties;
    /**
     * @type {(undefined|!Schema)}
     * @public
     */
    Schema.prototype.propertyNames;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.dependentRequired;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.dependentSchemas;
    /**
     * @type {(undefined|?)}
     * @public
     */
    Schema.prototype.dependencies;
    /**
     * @type {(undefined|!Array<!Array<(boolean|!Schema)>>)}
     * @public
     */
    Schema.prototype.prefixItems;
    /**
     * @type {(undefined|boolean|!Array<(boolean|!Schema)>|!Schema)}
     * @public
     */
    Schema.prototype.items;
    /**
     * @type {(undefined|boolean|!Schema)}
     * @public
     */
    Schema.prototype.additionalItems;
    /**
     * @type {(undefined|boolean|!Schema)}
     * @public
     */
    Schema.prototype.unevaluatedItems;
    /**
     * @type {(undefined|boolean|!Schema)}
     * @public
     */
    Schema.prototype.contains;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.minContains;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.maxContains;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.minItems;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.maxItems;
    /**
     * @type {(undefined|boolean)}
     * @public
     */
    Schema.prototype.uniqueItems;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.minimum;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.maximum;
    /**
     * @type {(undefined|number|boolean)}
     * @public
     */
    Schema.prototype.exclusiveMinimum;
    /**
     * @type {(undefined|number|boolean)}
     * @public
     */
    Schema.prototype.exclusiveMaximum;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.multipleOf;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.minLength;
    /**
     * @type {(undefined|number)}
     * @public
     */
    Schema.prototype.maxLength;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.pattern;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.__absolute_ref__;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.__absolute_recursive_ref__;
    /**
     * @type {(undefined|string)}
     * @public
     */
    Schema.prototype.__absolute_uri__;
    /* Skipping unhandled member: [key: string]: any;*/
}
/**
 * @record
 */
function OutputUnit() { }
exports.OutputUnit = OutputUnit;
/* istanbul ignore if */
if (false) {
    /**
     * @type {string}
     * @public
     */
    OutputUnit.prototype.keyword;
    /**
     * @type {string}
     * @public
     */
    OutputUnit.prototype.keywordLocation;
    /**
     * @type {string}
     * @public
     */
    OutputUnit.prototype.instanceLocation;
    /**
     * @type {string}
     * @public
     */
    OutputUnit.prototype.error;
}
/**
 * @record
 */
function ValidationResult() { }
exports.ValidationResult = ValidationResult;
/* istanbul ignore if */
if (false) {
    /**
     * @type {boolean}
     * @public
     */
    ValidationResult.prototype.valid;
    /**
     * @type {!Array<!OutputUnit>}
     * @public
     */
    ValidationResult.prototype.errors;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/ucs2-length.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.ucs2$2dlength');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/ucs2-length.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
/**
 * Get UCS-2 length of a string
 * https://mathiasbynens.be/notes/javascript-encoding
 * https://github.com/bestiejs/punycode.js - punycode.ucs2.decode
 * @param {string} s
 * @return {number}
 */
function ucs2length(s) {
    /** @type {number} */
    let result = 0;
    /** @type {number} */
    let length = s.length;
    /** @type {number} */
    let index = 0;
    /** @type {number} */
    let charCode;
    while (index < length) {
        result++;
        charCode = s.charCodeAt(index++);
        if (charCode >= 0xd800 && charCode <= 0xdbff && index < length) {
            // high surrogate, and there is a next character
            charCode = s.charCodeAt(index);
            if ((charCode & 0xfc00) == 0xdc00) {
                // low surrogate
                index++;
            }
        }
    }
    return result;
}
exports.ucs2length = ucs2length;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/validate.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.validate');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/validate.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_deep_compare_strict_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.deep$2dcompare$2dstrict");
const tsickle_dereference_2 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.dereference");
const tsickle_format_3 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.format");
const tsickle_pointer_4 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.pointer");
const tsickle_types_5 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.types");
const tsickle_ucs2_length_6 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.ucs2$2dlength");
const deep_compare_strict_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.deep$2dcompare$2dstrict');
const dereference_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.dereference');
const format_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.format');
const pointer_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.pointer');
const ucs2_length_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.ucs2$2dlength');
/** @typedef {?} */
exports.Evaluated;
/**
 * @param {?} instance
 * @param {(boolean|!tsickle_types_5.Schema)} schema
 * @param {string=} draft
 * @param {?=} lookup
 * @param {boolean=} shortCircuit
 * @param {(null|!tsickle_types_5.Schema)=} recursiveAnchor
 * @param {string=} instanceLocation
 * @param {string=} schemaLocation
 * @param {?=} evaluated
 * @return {!tsickle_types_5.ValidationResult}
 */
function validate(instance, schema, draft = '2019-09', lookup = (0, dereference_js_1.dereference)(schema), shortCircuit = true, recursiveAnchor = null, instanceLocation = '#', schemaLocation = '#', evaluated = Object.create(null)) {
    if (schema === true) {
        return { valid: true, errors: [] };
    }
    if (schema === false) {
        return {
            valid: false,
            errors: [
                {
                    instanceLocation,
                    keyword: 'false',
                    keywordLocation: instanceLocation,
                    error: 'False boolean schema.'
                }
            ]
        };
    }
    /** @type {string} */
    const rawInstanceType = typeof instance;
    /** @type {string} */
    let instanceType;
    switch (rawInstanceType) {
        case 'boolean':
        case 'number':
        case 'string':
            instanceType = rawInstanceType;
            break;
        case 'object':
            if (instance === null) {
                instanceType = 'null';
            }
            else if (Array.isArray(instance)) {
                instanceType = 'array';
            }
            else {
                instanceType = 'object';
            }
            break;
        default:
            // undefined, bigint, function, symbol
            throw new Error(`Instances of "${rawInstanceType}" type are not supported.`);
    }
    const { $ref, $recursiveRef, $recursiveAnchor, type: $type, const: $const, enum: $enum, required: $required, not: $not, anyOf: $anyOf, allOf: $allOf, oneOf: $oneOf, if: $if, then: $then, else: $else, format: $format, properties: $properties, patternProperties: $patternProperties, additionalProperties: $additionalProperties, unevaluatedProperties: $unevaluatedProperties, minProperties: $minProperties, maxProperties: $maxProperties, propertyNames: $propertyNames, dependentRequired: $dependentRequired, dependentSchemas: $dependentSchemas, dependencies: $dependencies, prefixItems: $prefixItems, items: $items, additionalItems: $additionalItems, unevaluatedItems: $unevaluatedItems, contains: $contains, minContains: $minContains, maxContains: $maxContains, minItems: $minItems, maxItems: $maxItems, uniqueItems: $uniqueItems, minimum: $minimum, maximum: $maximum, exclusiveMinimum: $exclusiveMinimum, exclusiveMaximum: $exclusiveMaximum, multipleOf: $multipleOf, minLength: $minLength, maxLength: $maxLength, pattern: $pattern, __absolute_ref__, __absolute_recursive_ref__ } = schema;
    /** @type {!Array<!tsickle_types_5.OutputUnit>} */
    const errors = [];
    if ($recursiveAnchor === true && recursiveAnchor === null) {
        recursiveAnchor = schema;
    }
    if ($recursiveRef === '#') {
        /** @type {!tsickle_types_5.Schema} */
        const refSchema = recursiveAnchor === null
            ? ((/** @type {!tsickle_types_5.Schema} */ (lookup[(/** @type {string} */ (__absolute_recursive_ref__))])))
            : recursiveAnchor;
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/$recursiveRef`;
        /** @type {!tsickle_types_5.ValidationResult} */
        const result = validate(instance, recursiveAnchor === null ? schema : recursiveAnchor, draft, lookup, shortCircuit, refSchema, instanceLocation, keywordLocation, evaluated);
        if (!result.valid) {
            errors.push({
                instanceLocation,
                keyword: '$recursiveRef',
                keywordLocation,
                error: 'A subschema had errors.'
            }, ...result.errors);
        }
    }
    if ($ref !== undefined) {
        /** @type {string} */
        const uri = __absolute_ref__ || $ref;
        /** @type {(boolean|!tsickle_types_5.Schema)} */
        const refSchema = lookup[uri];
        if (refSchema === undefined) {
            /** @type {string} */
            let message = `Unresolved $ref "${$ref}".`;
            if (__absolute_ref__ && __absolute_ref__ !== $ref) {
                message += `  Absolute URI "${__absolute_ref__}".`;
            }
            message += `\nKnown schemas:\n- ${Object.keys(lookup).join('\n- ')}`;
            throw new Error(message);
        }
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/$ref`;
        /** @type {!tsickle_types_5.ValidationResult} */
        const result = validate(instance, refSchema, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, keywordLocation, evaluated);
        if (!result.valid) {
            errors.push({
                instanceLocation,
                keyword: '$ref',
                keywordLocation,
                error: 'A subschema had errors.'
            }, ...result.errors);
        }
        if (draft === '4' || draft === '7') {
            return { valid: errors.length === 0, errors };
        }
    }
    if (Array.isArray($type)) {
        /** @type {number} */
        let length = (/** @type {!Array<string>} */ ($type)).length;
        /** @type {boolean} */
        let valid = false;
        for (let i = 0; i < length; i++) {
            if (instanceType === $type[i] ||
                ($type[i] === 'integer' &&
                    instanceType === 'number' &&
                    instance % 1 === 0 &&
                    instance === instance)) {
                valid = true;
                break;
            }
        }
        if (!valid) {
            errors.push({
                instanceLocation,
                keyword: 'type',
                keywordLocation: `${schemaLocation}/type`,
                error: `Instance type "${instanceType}" is invalid. Expected "${(/** @type {!Array<string>} */ ($type)).join('", "')}".`
            });
        }
    }
    else if ($type === 'integer') {
        if (instanceType !== 'number' || instance % 1 || instance !== instance) {
            errors.push({
                instanceLocation,
                keyword: 'type',
                keywordLocation: `${schemaLocation}/type`,
                error: `Instance type "${instanceType}" is invalid. Expected "${$type}".`
            });
        }
    }
    else if ($type !== undefined && instanceType !== $type) {
        errors.push({
            instanceLocation,
            keyword: 'type',
            keywordLocation: `${schemaLocation}/type`,
            error: `Instance type "${instanceType}" is invalid. Expected "${$type}".`
        });
    }
    if ($const !== undefined) {
        if (instanceType === 'object' || instanceType === 'array') {
            if (!(0, deep_compare_strict_js_1.deepCompareStrict)(instance, $const)) {
                errors.push({
                    instanceLocation,
                    keyword: 'const',
                    keywordLocation: `${schemaLocation}/const`,
                    error: `Instance does not match ${JSON.stringify($const)}.`
                });
            }
        }
        else if (instance !== $const) {
            errors.push({
                instanceLocation,
                keyword: 'const',
                keywordLocation: `${schemaLocation}/const`,
                error: `Instance does not match ${JSON.stringify($const)}.`
            });
        }
    }
    if ($enum !== undefined) {
        if (instanceType === 'object' || instanceType === 'array') {
            if (!$enum.some((/**
             * @param {?} value
             * @return {boolean}
             */
            value => (0, deep_compare_strict_js_1.deepCompareStrict)(instance, value)))) {
                errors.push({
                    instanceLocation,
                    keyword: 'enum',
                    keywordLocation: `${schemaLocation}/enum`,
                    error: `Instance does not match any of ${JSON.stringify($enum)}.`
                });
            }
        }
        else if (!$enum.some((/**
         * @param {?} value
         * @return {boolean}
         */
        value => instance === value))) {
            errors.push({
                instanceLocation,
                keyword: 'enum',
                keywordLocation: `${schemaLocation}/enum`,
                error: `Instance does not match any of ${JSON.stringify($enum)}.`
            });
        }
    }
    if ($not !== undefined) {
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/not`;
        /** @type {!tsickle_types_5.ValidationResult} */
        const result = validate(instance, $not, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, keywordLocation /*,
        evaluated*/);
        if (result.valid) {
            errors.push({
                instanceLocation,
                keyword: 'not',
                keywordLocation,
                error: 'Instance matched "not" schema.'
            });
        }
    }
    /** @type {!Array<?>} */
    let subEvaluateds = [];
    if ($anyOf !== undefined) {
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/anyOf`;
        /** @type {number} */
        const errorsLength = errors.length;
        /** @type {boolean} */
        let anyValid = false;
        for (let i = 0; i < $anyOf.length; i++) {
            /** @type {!tsickle_types_5.Schema} */
            const subSchema = $anyOf[i];
            /** @type {?} */
            const subEvaluated = Object.create(evaluated);
            /** @type {!tsickle_types_5.ValidationResult} */
            const result = validate(instance, subSchema, draft, lookup, shortCircuit, $recursiveAnchor === true ? recursiveAnchor : null, instanceLocation, `${keywordLocation}/${i}`, subEvaluated);
            errors.push(...result.errors);
            anyValid = anyValid || result.valid;
            if (result.valid) {
                subEvaluateds.push(subEvaluated);
            }
        }
        if (anyValid) {
            errors.length = errorsLength;
        }
        else {
            errors.splice(errorsLength, 0, {
                instanceLocation,
                keyword: 'anyOf',
                keywordLocation,
                error: 'Instance does not match any subschemas.'
            });
        }
    }
    if ($allOf !== undefined) {
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/allOf`;
        /** @type {number} */
        const errorsLength = errors.length;
        /** @type {boolean} */
        let allValid = true;
        for (let i = 0; i < $allOf.length; i++) {
            /** @type {!tsickle_types_5.Schema} */
            const subSchema = $allOf[i];
            /** @type {?} */
            const subEvaluated = Object.create(evaluated);
            /** @type {!tsickle_types_5.ValidationResult} */
            const result = validate(instance, subSchema, draft, lookup, shortCircuit, $recursiveAnchor === true ? recursiveAnchor : null, instanceLocation, `${keywordLocation}/${i}`, subEvaluated);
            errors.push(...result.errors);
            allValid = allValid && result.valid;
            if (result.valid) {
                subEvaluateds.push(subEvaluated);
            }
        }
        if (allValid) {
            errors.length = errorsLength;
        }
        else {
            errors.splice(errorsLength, 0, {
                instanceLocation,
                keyword: 'allOf',
                keywordLocation,
                error: `Instance does not match every subschema.`
            });
        }
    }
    if ($oneOf !== undefined) {
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/oneOf`;
        /** @type {number} */
        const errorsLength = errors.length;
        /** @type {number} */
        const matches = $oneOf.filter((/**
         * @param {!tsickle_types_5.Schema} subSchema
         * @param {number} i
         * @return {boolean}
         */
        (subSchema, i) => {
            /** @type {?} */
            const subEvaluated = Object.create(evaluated);
            /** @type {!tsickle_types_5.ValidationResult} */
            const result = validate(instance, subSchema, draft, lookup, shortCircuit, $recursiveAnchor === true ? recursiveAnchor : null, instanceLocation, `${keywordLocation}/${i}`, subEvaluated);
            errors.push(...result.errors);
            if (result.valid) {
                subEvaluateds.push(subEvaluated);
            }
            return result.valid;
        })).length;
        if (matches === 1) {
            errors.length = errorsLength;
        }
        else {
            errors.splice(errorsLength, 0, {
                instanceLocation,
                keyword: 'oneOf',
                keywordLocation,
                error: `Instance does not match exactly one subschema (${matches} matches).`
            });
        }
    }
    if (instanceType === 'object' || instanceType === 'array') {
        Object.assign(evaluated, ...subEvaluateds);
    }
    if ($if !== undefined) {
        /** @type {string} */
        const keywordLocation = `${schemaLocation}/if`;
        /** @type {boolean} */
        const conditionResult = validate(instance, $if, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, keywordLocation, evaluated).valid;
        if (conditionResult) {
            if ($then !== undefined) {
                /** @type {!tsickle_types_5.ValidationResult} */
                const thenResult = validate(instance, $then, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, `${schemaLocation}/then`, evaluated);
                if (!thenResult.valid) {
                    errors.push({
                        instanceLocation,
                        keyword: 'if',
                        keywordLocation,
                        error: `Instance does not match "then" schema.`
                    }, ...thenResult.errors);
                }
            }
        }
        else if ($else !== undefined) {
            /** @type {!tsickle_types_5.ValidationResult} */
            const elseResult = validate(instance, $else, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, `${schemaLocation}/else`, evaluated);
            if (!elseResult.valid) {
                errors.push({
                    instanceLocation,
                    keyword: 'if',
                    keywordLocation,
                    error: `Instance does not match "else" schema.`
                }, ...elseResult.errors);
            }
        }
    }
    if (instanceType === 'object') {
        if ($required !== undefined) {
            for (const key of $required) {
                if (!(key in instance)) {
                    errors.push({
                        instanceLocation,
                        keyword: 'required',
                        keywordLocation: `${schemaLocation}/required`,
                        error: `Instance does not have required property "${key}".`
                    });
                }
            }
        }
        /** @type {!Array<string>} */
        const keys = Object.keys(instance);
        if ($minProperties !== undefined && keys.length < $minProperties) {
            errors.push({
                instanceLocation,
                keyword: 'minProperties',
                keywordLocation: `${schemaLocation}/minProperties`,
                error: `Instance does not have at least ${$minProperties} properties.`
            });
        }
        if ($maxProperties !== undefined && keys.length > $maxProperties) {
            errors.push({
                instanceLocation,
                keyword: 'maxProperties',
                keywordLocation: `${schemaLocation}/maxProperties`,
                error: `Instance does not have at least ${$maxProperties} properties.`
            });
        }
        if ($propertyNames !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/propertyNames`;
            for (const key in instance) {
                /** @type {string} */
                const subInstancePointer = `${instanceLocation}/${(0, pointer_js_1.encodePointer)(key)}`;
                /** @type {!tsickle_types_5.ValidationResult} */
                const result = validate(key, $propertyNames, draft, lookup, shortCircuit, recursiveAnchor, subInstancePointer, keywordLocation);
                if (!result.valid) {
                    errors.push({
                        instanceLocation,
                        keyword: 'propertyNames',
                        keywordLocation,
                        error: `Property name "${key}" does not match schema.`
                    }, ...result.errors);
                }
            }
        }
        if ($dependentRequired !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/dependantRequired`;
            for (const key in $dependentRequired) {
                if (key in instance) {
                    /** @type {!Array<string>} */
                    const required = (/** @type {!Array<string>} */ ($dependentRequired[key]));
                    for (const dependantKey of required) {
                        if (!(dependantKey in instance)) {
                            errors.push({
                                instanceLocation,
                                keyword: 'dependentRequired',
                                keywordLocation,
                                error: `Instance has "${key}" but does not have "${dependantKey}".`
                            });
                        }
                    }
                }
            }
        }
        if ($dependentSchemas !== undefined) {
            for (const key in $dependentSchemas) {
                /** @type {string} */
                const keywordLocation = `${schemaLocation}/dependentSchemas`;
                if (key in instance) {
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance, $dependentSchemas[key], draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, `${keywordLocation}/${(0, pointer_js_1.encodePointer)(key)}`, evaluated);
                    if (!result.valid) {
                        errors.push({
                            instanceLocation,
                            keyword: 'dependentSchemas',
                            keywordLocation,
                            error: `Instance has "${key}" but does not match dependant schema.`
                        }, ...result.errors);
                    }
                }
            }
        }
        if ($dependencies !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/dependencies`;
            for (const key in $dependencies) {
                if (key in instance) {
                    /** @type {(!Array<string>|!tsickle_types_5.Schema)} */
                    const propsOrSchema = (/** @type {(!Array<string>|!tsickle_types_5.Schema)} */ ($dependencies[key]));
                    if (Array.isArray(propsOrSchema)) {
                        for (const dependantKey of propsOrSchema) {
                            if (!(dependantKey in instance)) {
                                errors.push({
                                    instanceLocation,
                                    keyword: 'dependencies',
                                    keywordLocation,
                                    error: `Instance has "${key}" but does not have "${dependantKey}".`
                                });
                            }
                        }
                    }
                    else {
                        /** @type {!tsickle_types_5.ValidationResult} */
                        const result = validate(instance, propsOrSchema, draft, lookup, shortCircuit, recursiveAnchor, instanceLocation, `${keywordLocation}/${(0, pointer_js_1.encodePointer)(key)}`);
                        if (!result.valid) {
                            errors.push({
                                instanceLocation,
                                keyword: 'dependencies',
                                keywordLocation,
                                error: `Instance has "${key}" but does not match dependant schema.`
                            }, ...result.errors);
                        }
                    }
                }
            }
        }
        /** @type {?} */
        const thisEvaluated = Object.create(null);
        /** @type {boolean} */
        let stop = false;
        if ($properties !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/properties`;
            for (const key in $properties) {
                if (!(key in instance)) {
                    continue;
                }
                /** @type {string} */
                const subInstancePointer = `${instanceLocation}/${(0, pointer_js_1.encodePointer)(key)}`;
                /** @type {!tsickle_types_5.ValidationResult} */
                const result = validate(instance[key], $properties[key], draft, lookup, shortCircuit, recursiveAnchor, subInstancePointer, `${keywordLocation}/${(0, pointer_js_1.encodePointer)(key)}`);
                if (result.valid) {
                    evaluated[key] = thisEvaluated[key] = true;
                }
                else {
                    stop = shortCircuit;
                    errors.push({
                        instanceLocation,
                        keyword: 'properties',
                        keywordLocation,
                        error: `Property "${key}" does not match schema.`
                    }, ...result.errors);
                    if (stop)
                        break;
                }
            }
        }
        if (!stop && $patternProperties !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/patternProperties`;
            for (const pattern in $patternProperties) {
                /** @type {!RegExp} */
                const regex = new RegExp(pattern);
                /** @type {(boolean|!tsickle_types_5.Schema)} */
                const subSchema = $patternProperties[pattern];
                for (const key in instance) {
                    if (!regex.test(key)) {
                        continue;
                    }
                    /** @type {string} */
                    const subInstancePointer = `${instanceLocation}/${(0, pointer_js_1.encodePointer)(key)}`;
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[key], subSchema, draft, lookup, shortCircuit, recursiveAnchor, subInstancePointer, `${keywordLocation}/${(0, pointer_js_1.encodePointer)(pattern)}`);
                    if (result.valid) {
                        evaluated[key] = thisEvaluated[key] = true;
                    }
                    else {
                        stop = shortCircuit;
                        errors.push({
                            instanceLocation,
                            keyword: 'patternProperties',
                            keywordLocation,
                            error: `Property "${key}" matches pattern "${pattern}" but does not match associated schema.`
                        }, ...result.errors);
                    }
                }
            }
        }
        if (!stop && $additionalProperties !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/additionalProperties`;
            for (const key in instance) {
                if (thisEvaluated[key]) {
                    continue;
                }
                /** @type {string} */
                const subInstancePointer = `${instanceLocation}/${(0, pointer_js_1.encodePointer)(key)}`;
                /** @type {!tsickle_types_5.ValidationResult} */
                const result = validate(instance[key], $additionalProperties, draft, lookup, shortCircuit, recursiveAnchor, subInstancePointer, keywordLocation);
                if (result.valid) {
                    evaluated[key] = true;
                }
                else {
                    stop = shortCircuit;
                    errors.push({
                        instanceLocation,
                        keyword: 'additionalProperties',
                        keywordLocation,
                        error: `Property "${key}" does not match additional properties schema.`
                    }, ...result.errors);
                }
            }
        }
        else if (!stop && $unevaluatedProperties !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/unevaluatedProperties`;
            for (const key in instance) {
                if (!evaluated[key]) {
                    /** @type {string} */
                    const subInstancePointer = `${instanceLocation}/${(0, pointer_js_1.encodePointer)(key)}`;
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[key], $unevaluatedProperties, draft, lookup, shortCircuit, recursiveAnchor, subInstancePointer, keywordLocation);
                    if (result.valid) {
                        evaluated[key] = true;
                    }
                    else {
                        errors.push({
                            instanceLocation,
                            keyword: 'unevaluatedProperties',
                            keywordLocation,
                            error: `Property "${key}" does not match unevaluated properties schema.`
                        }, ...result.errors);
                    }
                }
            }
        }
    }
    else if (instanceType === 'array') {
        if ($maxItems !== undefined && instance.length > $maxItems) {
            errors.push({
                instanceLocation,
                keyword: 'maxItems',
                keywordLocation: `${schemaLocation}/maxItems`,
                error: `Array has too many items (${instance.length} > ${$maxItems}).`
            });
        }
        if ($minItems !== undefined && instance.length < $minItems) {
            errors.push({
                instanceLocation,
                keyword: 'minItems',
                keywordLocation: `${schemaLocation}/minItems`,
                error: `Array has too few items (${instance.length} < ${$minItems}).`
            });
        }
        /** @type {number} */
        const length = instance.length;
        /** @type {number} */
        let i = 0;
        /** @type {boolean} */
        let stop = false;
        if ($prefixItems !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/prefixItems`;
            /** @type {number} */
            const length2 = Math.min($prefixItems.length, length);
            for (; i < length2; i++) {
                /** @type {!tsickle_types_5.ValidationResult} */
                const result = validate(instance[i], $prefixItems[i], draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${i}`, `${keywordLocation}/${i}`);
                evaluated[i] = true;
                if (!result.valid) {
                    stop = shortCircuit;
                    errors.push({
                        instanceLocation,
                        keyword: 'prefixItems',
                        keywordLocation,
                        error: `Items did not match schema.`
                    }, ...result.errors);
                    if (stop)
                        break;
                }
            }
        }
        if ($items !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/items`;
            if (Array.isArray($items)) {
                /** @type {number} */
                const length2 = Math.min((/** @type {!Array<(boolean|!tsickle_types_5.Schema)>} */ ($items)).length, length);
                for (; i < length2; i++) {
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[i], $items[i], draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${i}`, `${keywordLocation}/${i}`);
                    evaluated[i] = true;
                    if (!result.valid) {
                        stop = shortCircuit;
                        errors.push({
                            instanceLocation,
                            keyword: 'items',
                            keywordLocation,
                            error: `Items did not match schema.`
                        }, ...result.errors);
                        if (stop)
                            break;
                    }
                }
            }
            else {
                for (; i < length; i++) {
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[i], $items, draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${i}`, keywordLocation);
                    evaluated[i] = true;
                    if (!result.valid) {
                        stop = shortCircuit;
                        errors.push({
                            instanceLocation,
                            keyword: 'items',
                            keywordLocation,
                            error: `Items did not match schema.`
                        }, ...result.errors);
                        if (stop)
                            break;
                    }
                }
            }
            if (!stop && $additionalItems !== undefined) {
                /** @type {string} */
                const keywordLocation = `${schemaLocation}/additionalItems`;
                for (; i < length; i++) {
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[i], $additionalItems, draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${i}`, keywordLocation);
                    evaluated[i] = true;
                    if (!result.valid) {
                        stop = shortCircuit;
                        errors.push({
                            instanceLocation,
                            keyword: 'additionalItems',
                            keywordLocation,
                            error: `Items did not match additional items schema.`
                        }, ...result.errors);
                    }
                }
            }
        }
        if ($contains !== undefined) {
            if (length === 0 && $minContains === undefined) {
                errors.push({
                    instanceLocation,
                    keyword: 'contains',
                    keywordLocation: `${schemaLocation}/contains`,
                    error: `Array is empty. It must contain at least one item matching the schema.`
                });
            }
            else if ($minContains !== undefined && length < $minContains) {
                errors.push({
                    instanceLocation,
                    keyword: 'minContains',
                    keywordLocation: `${schemaLocation}/minContains`,
                    error: `Array has less items (${length}) than minContains (${$minContains}).`
                });
            }
            else {
                /** @type {string} */
                const keywordLocation = `${schemaLocation}/contains`;
                /** @type {number} */
                const errorsLength = errors.length;
                /** @type {number} */
                let contained = 0;
                for (let j = 0; j < length; j++) {
                    /** @type {!tsickle_types_5.ValidationResult} */
                    const result = validate(instance[j], $contains, draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${j}`, keywordLocation);
                    if (result.valid) {
                        evaluated[j] = true;
                        contained++;
                    }
                    else {
                        errors.push(...result.errors);
                    }
                }
                if (contained >= ($minContains || 0)) {
                    errors.length = errorsLength;
                }
                if ($minContains === undefined &&
                    $maxContains === undefined &&
                    contained === 0) {
                    errors.splice(errorsLength, 0, {
                        instanceLocation,
                        keyword: 'contains',
                        keywordLocation,
                        error: `Array does not contain item matching schema.`
                    });
                }
                else if ($minContains !== undefined && contained < $minContains) {
                    errors.push({
                        instanceLocation,
                        keyword: 'minContains',
                        keywordLocation: `${schemaLocation}/minContains`,
                        error: `Array must contain at least ${$minContains} items matching schema. Only ${contained} items were found.`
                    });
                }
                else if ($maxContains !== undefined && contained > $maxContains) {
                    errors.push({
                        instanceLocation,
                        keyword: 'maxContains',
                        keywordLocation: `${schemaLocation}/maxContains`,
                        error: `Array may contain at most ${$maxContains} items matching schema. ${contained} items were found.`
                    });
                }
            }
        }
        if (!stop && $unevaluatedItems !== undefined) {
            /** @type {string} */
            const keywordLocation = `${schemaLocation}/unevaluatedItems`;
            for (i; i < length; i++) {
                if (evaluated[i]) {
                    continue;
                }
                /** @type {!tsickle_types_5.ValidationResult} */
                const result = validate(instance[i], $unevaluatedItems, draft, lookup, shortCircuit, recursiveAnchor, `${instanceLocation}/${i}`, keywordLocation);
                evaluated[i] = true;
                if (!result.valid) {
                    errors.push({
                        instanceLocation,
                        keyword: 'unevaluatedItems',
                        keywordLocation,
                        error: `Items did not match unevaluated items schema.`
                    }, ...result.errors);
                }
            }
        }
        if ($uniqueItems) {
            for (let j = 0; j < length; j++) {
                /** @type {?} */
                const a = instance[j];
                /** @type {boolean} */
                const ao = typeof a === 'object' && a !== null;
                for (let k = 0; k < length; k++) {
                    if (j === k) {
                        continue;
                    }
                    /** @type {?} */
                    const b = instance[k];
                    /** @type {boolean} */
                    const bo = typeof b === 'object' && b !== null;
                    if (a === b || (ao && bo && (0, deep_compare_strict_js_1.deepCompareStrict)(a, b))) {
                        errors.push({
                            instanceLocation,
                            keyword: 'uniqueItems',
                            keywordLocation: `${schemaLocation}/uniqueItems`,
                            error: `Duplicate items at indexes ${j} and ${k}.`
                        });
                        j = Number.MAX_SAFE_INTEGER;
                        k = Number.MAX_SAFE_INTEGER;
                    }
                }
            }
        }
    }
    else if (instanceType === 'number') {
        if (draft === '4') {
            if ($minimum !== undefined &&
                (($exclusiveMinimum === true && instance <= $minimum) ||
                    instance < $minimum)) {
                errors.push({
                    instanceLocation,
                    keyword: 'minimum',
                    keywordLocation: `${schemaLocation}/minimum`,
                    error: `${instance} is less than ${$exclusiveMinimum ? 'or equal to ' : ''} ${$minimum}.`
                });
            }
            if ($maximum !== undefined &&
                (($exclusiveMaximum === true && instance >= $maximum) ||
                    instance > $maximum)) {
                errors.push({
                    instanceLocation,
                    keyword: 'maximum',
                    keywordLocation: `${schemaLocation}/maximum`,
                    error: `${instance} is greater than ${$exclusiveMaximum ? 'or equal to ' : ''} ${$maximum}.`
                });
            }
        }
        else {
            if ($minimum !== undefined && instance < $minimum) {
                errors.push({
                    instanceLocation,
                    keyword: 'minimum',
                    keywordLocation: `${schemaLocation}/minimum`,
                    error: `${instance} is less than ${$minimum}.`
                });
            }
            if ($maximum !== undefined && instance > $maximum) {
                errors.push({
                    instanceLocation,
                    keyword: 'maximum',
                    keywordLocation: `${schemaLocation}/maximum`,
                    error: `${instance} is greater than ${$maximum}.`
                });
            }
            if ($exclusiveMinimum !== undefined && instance <= $exclusiveMinimum) {
                errors.push({
                    instanceLocation,
                    keyword: 'exclusiveMinimum',
                    keywordLocation: `${schemaLocation}/exclusiveMinimum`,
                    error: `${instance} is less than ${$exclusiveMinimum}.`
                });
            }
            if ($exclusiveMaximum !== undefined && instance >= $exclusiveMaximum) {
                errors.push({
                    instanceLocation,
                    keyword: 'exclusiveMaximum',
                    keywordLocation: `${schemaLocation}/exclusiveMaximum`,
                    error: `${instance} is greater than or equal to ${$exclusiveMaximum}.`
                });
            }
        }
        if ($multipleOf !== undefined) {
            /** @type {number} */
            const remainder = instance % $multipleOf;
            if (Math.abs(0 - remainder) >= 1.1920929e-7 &&
                Math.abs($multipleOf - remainder) >= 1.1920929e-7) {
                errors.push({
                    instanceLocation,
                    keyword: 'multipleOf',
                    keywordLocation: `${schemaLocation}/multipleOf`,
                    error: `${instance} is not a multiple of ${$multipleOf}.`
                });
            }
        }
    }
    else if (instanceType === 'string') {
        /** @type {number} */
        const length = $minLength === undefined && $maxLength === undefined
            ? 0
            : (0, ucs2_length_js_1.ucs2length)(instance);
        if ($minLength !== undefined && length < $minLength) {
            errors.push({
                instanceLocation,
                keyword: 'minLength',
                keywordLocation: `${schemaLocation}/minLength`,
                error: `String is too short (${length} < ${$minLength}).`
            });
        }
        if ($maxLength !== undefined && length > $maxLength) {
            errors.push({
                instanceLocation,
                keyword: 'maxLength',
                keywordLocation: `${schemaLocation}/maxLength`,
                error: `String is too long (${length} > ${$maxLength}).`
            });
        }
        if ($pattern !== undefined && !new RegExp($pattern).test(instance)) {
            errors.push({
                instanceLocation,
                keyword: 'pattern',
                keywordLocation: `${schemaLocation}/pattern`,
                error: `String does not match pattern.`
            });
        }
        if ($format !== undefined &&
            format_js_1.fastFormat[$format] &&
            !format_js_1.fastFormat[$format](instance)) {
            errors.push({
                instanceLocation,
                keyword: 'format',
                keywordLocation: `${schemaLocation}/format`,
                error: `String does not match format "${$format}".`
            });
        }
    }
    return { valid: errors.length === 0, errors };
}
exports.validate = validate;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/validator.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.validator');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/validator.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_dereference_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.dereference");
const tsickle_types_2 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.types");
const tsickle_validate_3 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.validate");
const dereference_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.dereference');
const validate_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.validate');
class Validator {
    /**
     * @public
     * @param {(boolean|!tsickle_types_2.Schema)} schema
     * @param {string=} draft
     * @param {boolean=} shortCircuit
     */
    constructor(schema, draft = '2019-09', shortCircuit = true) {
        this.schema = schema;
        this.draft = draft;
        this.shortCircuit = shortCircuit;
        this.lookup = (0, dereference_js_1.dereference)(schema);
    }
    /**
     * @public
     * @param {?} instance
     * @return {!tsickle_types_2.ValidationResult}
     */
    validate(instance) {
        return (0, validate_js_1.validate)(instance, this.schema, this.draft, this.lookup, this.shortCircuit);
    }
    /**
     * @public
     * @param {!tsickle_types_2.Schema} schema
     * @param {(undefined|string)=} id
     * @return {void}
     */
    addSchema(schema, id) {
        if (id) {
            schema = { ...schema, $id: id };
        }
        (0, dereference_js_1.dereference)(schema, this.lookup);
    }
}
exports.Validator = Validator;
/* istanbul ignore if */
if (false) {
    /**
     * @const {?}
     * @private
     */
    Validator.prototype.lookup;
    /**
     * @const {(boolean|!tsickle_types_2.Schema)}
     * @private
     */
    Validator.prototype.schema;
    /**
     * @const {string}
     * @private
     */
    Validator.prototype.draft;
    /**
     * @const {boolean}
     * @private
     */
    Validator.prototype.shortCircuit;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2020 Jeremy Danyow
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 * associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
 * NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/cfworker_json_schema/src/index.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.cfworker_json_schema.src.index');
var module = module || { id: 'third_party/javascript/cfworker_json_schema/src/index.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_deep_compare_strict_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.deep$2dcompare$2dstrict");
const tsickle_dereference_2 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.dereference");
const tsickle_format_3 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.format");
const tsickle_pointer_4 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.pointer");
const tsickle_types_5 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.types");
const tsickle_ucs2_length_6 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.ucs2$2dlength");
const tsickle_validate_7 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.validate");
const tsickle_validator_8 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.validator");
const deep_compare_strict_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.deep$2dcompare$2dstrict');
exports.deepCompareStrict = deep_compare_strict_js_1.deepCompareStrict;
const dereference_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.dereference');
exports.dereference = dereference_js_1.dereference;
exports.schemaKeyword = dereference_js_1.schemaKeyword;
exports.schemaArrayKeyword = dereference_js_1.schemaArrayKeyword;
exports.schemaMapKeyword = dereference_js_1.schemaMapKeyword;
exports.ignoredKeyword = dereference_js_1.ignoredKeyword;
exports.initialBaseURI = dereference_js_1.initialBaseURI;
const format_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.format');
exports.fullFormat = format_js_1.fullFormat;
exports.fastFormat = format_js_1.fastFormat;
const pointer_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.pointer');
exports.encodePointer = pointer_js_1.encodePointer;
exports.escapePointer = pointer_js_1.escapePointer;
const types_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.types');
exports.OutputFormat = types_js_1.OutputFormat;
/** @typedef {!tsickle_types_5.SchemaDraft} */
exports.SchemaDraft; // re-export typedef
/** @typedef {!tsickle_types_5.InstanceType} */
exports.InstanceType; // re-export typedef
/** @typedef {!tsickle_types_5.Schema} */
exports.Schema; // re-export typedef
/** @typedef {!tsickle_types_5.OutputUnit} */
exports.OutputUnit; // re-export typedef
/** @typedef {!tsickle_types_5.ValidationResult} */
exports.ValidationResult; // re-export typedef
const ucs2_length_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.ucs2$2dlength');
exports.ucs2length = ucs2_length_js_1.ucs2length;
const validate_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.validate');
exports.validate = validate_js_1.validate;
/** @typedef {!tsickle_validate_7.Evaluated} */
exports.Evaluated; // re-export typedef
const validator_js_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.validator');
exports.Validator = validator_js_1.Validator;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2024 Anthropic, PBC
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/modelcontextprotocol/src/shared/protocol.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.modelcontextprotocol.src.shared.protocol');
var module = module || { id: 'third_party/javascript/modelcontextprotocol/src/shared/protocol.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_zod_1 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.index");
const tsickle_types_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.types");
const tsickle_transport_3 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.shared.transport");
const tsickle_types_4 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.server.auth.types");
const types_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.types');
/**
 * Callback for progress notifications.
 * @typedef {function(?): void}
 */
exports.ProgressCallback;
/**
 * Additional initialization options.
 * @typedef {{enforceStrictCapabilities: (undefined|boolean)}}
 */
exports.ProtocolOptions;
/**
 * The default request timeout, in miliseconds.
 * @type {number}
 */
exports.DEFAULT_REQUEST_TIMEOUT_MSEC = 60000;
/**
 * Options that can be given per request.
 * @typedef {?}
 */
exports.RequestOptions;
/**
 * Options that can be given per notification.
 * @typedef {{relatedRequestId: (undefined|string|number)}}
 */
exports.NotificationOptions;
/**
 * Extra data given to request handlers.
 * @typedef {{signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(?): !Promise<void>, sendRequest: function(?, ?, (undefined|?)=): !Promise<?>}}
 */
exports.RequestHandlerExtra;
/**
 * Information about a request's timeout state
 * @typedef {{timeoutId: number, startTime: number, timeout: number, maxTotalTimeout: (undefined|number), resetTimeoutOnProgress: boolean, onTimeout: function(): void}}
 */
var TimeoutInfo;
/**
 * Implements MCP protocol framing on top of a pluggable transport, including
 * features like request/response linking, notifications, and progress.
 * @abstract
 * @template SendRequestT, SendNotificationT, SendResultT
 */
class Protocol {
    /**
     * @public
     * @param {(undefined|{enforceStrictCapabilities: (undefined|boolean)})=} _options
     */
    constructor(_options) {
        this._options = _options;
        this._requestMessageId = 0;
        this._requestHandlers = new Map();
        this._requestHandlerAbortControllers = new Map();
        this._notificationHandlers = new Map();
        this._responseHandlers = new Map();
        this._progressHandlers = new Map();
        this._timeoutInfo = new Map();
        this.setNotificationHandler(types_1.CancelledNotificationSchema, (/**
         * @param {{method: string, params: ?}} notification
         * @return {void}
         */
        (notification) => {
            /** @type {(undefined|!AbortController)} */
            const controller = this._requestHandlerAbortControllers.get(notification.params.requestId);
            controller?.abort(notification.params.reason);
        }));
        this.setNotificationHandler(types_1.ProgressNotificationSchema, (/**
         * @param {{method: string, params: ?}} notification
         * @return {void}
         */
        (notification) => {
            this._onprogress((/** @type {?} */ ((/** @type {*} */ (notification)))));
        }));
        this.setRequestHandler(types_1.PingRequestSchema, (
        // Automatic pong by default.
        /**
         * @param {{params: (undefined|?), method: string}} _request
         * @return {SendResultT}
         */
        (_request) => (/** @type {SendResultT} */ (({})))));
    }
    /**
     * @private
     * @param {number} messageId
     * @param {number} timeout
     * @param {(undefined|number)} maxTotalTimeout
     * @param {function(): void} onTimeout
     * @param {boolean=} resetTimeoutOnProgress
     * @return {void}
     */
    _setupTimeout(messageId, timeout, maxTotalTimeout, onTimeout, resetTimeoutOnProgress = false) {
        this._timeoutInfo.set(messageId, {
            timeoutId: setTimeout(onTimeout, timeout),
            startTime: Date.now(),
            timeout,
            maxTotalTimeout,
            resetTimeoutOnProgress,
            onTimeout
        });
    }
    /**
     * @private
     * @param {number} messageId
     * @return {boolean}
     */
    _resetTimeout(messageId) {
        /** @type {(undefined|{timeoutId: number, startTime: number, timeout: number, maxTotalTimeout: (undefined|number), resetTimeoutOnProgress: boolean, onTimeout: function(): void})} */
        const info = this._timeoutInfo.get(messageId);
        if (!info)
            return false;
        /** @type {number} */
        const totalElapsed = Date.now() - info.startTime;
        if (info.maxTotalTimeout && totalElapsed >= info.maxTotalTimeout) {
            this._timeoutInfo.delete(messageId);
            throw new types_1.McpError(types_1.ErrorCode.RequestTimeout, "Maximum total timeout exceeded", { maxTotalTimeout: info.maxTotalTimeout, totalElapsed });
        }
        clearTimeout(info.timeoutId);
        info.timeoutId = setTimeout(info.onTimeout, info.timeout);
        return true;
    }
    /**
     * @private
     * @param {number} messageId
     * @return {void}
     */
    _cleanupTimeout(messageId) {
        /** @type {(undefined|{timeoutId: number, startTime: number, timeout: number, maxTotalTimeout: (undefined|number), resetTimeoutOnProgress: boolean, onTimeout: function(): void})} */
        const info = this._timeoutInfo.get(messageId);
        if (info) {
            clearTimeout(info.timeoutId);
            this._timeoutInfo.delete(messageId);
        }
    }
    /**
     * Attaches to the given transport, starts it, and starts listening for messages.
     *
     * The Protocol object assumes ownership of the Transport, replacing any callbacks that have already been set, and expects that it is the only user of the Transport instance going forward.
     * @public
     * @param {!tsickle_transport_3.Transport} transport
     * @return {!Promise<void>}
     */
    async connect(transport) {
        this._transport = transport;
        this._transport.onclose = (/**
         * @return {void}
         */
        () => {
            this._onclose();
        });
        this._transport.onerror = (/**
         * @param {!Error} error
         * @return {void}
         */
        (error) => {
            this._onerror(error);
        });
        this._transport.onmessage = (/**
         * @param {?} message
         * @param {(undefined|!tsickle_types_2.MessageExtraInfo)} extra
         * @return {void}
         */
        (message, extra) => {
            if ((0, types_1.isJSONRPCResponse)(message) || (0, types_1.isJSONRPCError)(message)) {
                this._onresponse(message);
            }
            else if ((0, types_1.isJSONRPCRequest)(message)) {
                this._onrequest(message, extra);
            }
            else if ((0, types_1.isJSONRPCNotification)(message)) {
                this._onnotification(message);
            }
            else {
                this._onerror(new Error(`Unknown message type: ${JSON.stringify(message)}`));
            }
        });
        await this._transport.start();
    }
    /**
     * @private
     * @return {void}
     */
    _onclose() {
        /** @type {!Map<number, function((!Error|?)): void>} */
        const responseHandlers = this._responseHandlers;
        this._responseHandlers = new Map();
        this._progressHandlers.clear();
        this._transport = undefined;
        this.onclose?.();
        /** @type {!tsickle_types_2.McpError} */
        const error = new types_1.McpError(types_1.ErrorCode.ConnectionClosed, "Connection closed");
        for (const handler of responseHandlers.values()) {
            handler(error);
        }
    }
    /**
     * @private
     * @param {!Error} error
     * @return {void}
     */
    _onerror(error) {
        this.onerror?.(error);
    }
    /**
     * @private
     * @param {?} notification
     * @return {void}
     */
    _onnotification(notification) {
        /** @type {(undefined|function(?): !Promise<void>)} */
        const handler = this._notificationHandlers.get(notification.method) ??
            this.fallbackNotificationHandler;
        // Ignore notifications not being subscribed to.
        if (handler === undefined) {
            return;
        }
        // Starting with Promise.resolve() puts any synchronous errors into the monad as well.
        Promise.resolve()
            .then((/**
         * @return {!Promise<void>}
         */
        () => handler(notification)))
            .catch((/**
         * @param {?} error
         * @return {void}
         */
        (error) => this._onerror(new Error(`Uncaught error in notification handler: ${error}`))));
    }
    /**
     * @private
     * @param {?} request
     * @param {(undefined|!tsickle_types_2.MessageExtraInfo)=} extra
     * @return {void}
     */
    _onrequest(request, extra) {
        /** @type {(undefined|function(?, {signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(SendNotificationT): !Promise<void>, sendRequest: function(SendRequestT, ?, (undefined|?)=): !Promise<?>}): !Promise<SendResultT>)} */
        const handler = this._requestHandlers.get(request.method) ?? this.fallbackRequestHandler;
        if (handler === undefined) {
            this._transport
                ?.send({
                jsonrpc: "2.0",
                id: request.id,
                error: {
                    code: types_1.ErrorCode.MethodNotFound,
                    message: "Method not found",
                },
            })
                .catch((/**
             * @param {?} error
             * @return {void}
             */
            (error) => this._onerror(new Error(`Failed to send an error response: ${error}`))));
            return;
        }
        /** @type {!AbortController} */
        const abortController = new AbortController();
        this._requestHandlerAbortControllers.set(request.id, abortController);
        /** @type {{signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(SendNotificationT): !Promise<void>, sendRequest: function(SendRequestT, ?, (undefined|?)=): !Promise<?>}} */
        const fullExtra = {
            signal: abortController.signal,
            sessionId: this._transport?.sessionId,
            _meta: request.params?._meta,
            sendNotification: (/**
             * @param {SendNotificationT} notification
             * @return {!Promise<void>}
             */
            (notification) => this.notification(notification, { relatedRequestId: request.id })),
            sendRequest: (/**
             * @param {SendRequestT} r
             * @param {?} resultSchema
             * @param {(undefined|?)=} options
             * @return {!Promise<?>}
             */
            (r, resultSchema, options) => this.request(r, resultSchema, { ...options, relatedRequestId: request.id })),
            authInfo: extra?.authInfo,
            requestId: request.id,
            requestInfo: extra?.requestInfo
        };
        // Starting with Promise.resolve() puts any synchronous errors into the monad as well.
        Promise.resolve()
            .then((/**
         * @return {!Promise<SendResultT>}
         */
        () => handler(request, fullExtra)))
            .then((/**
         * @param {SendResultT} result
         * @return {(undefined|!Promise<void>)}
         */
        (result) => {
            if (abortController.signal.aborted) {
                return;
            }
            return this._transport?.send({
                result,
                jsonrpc: "2.0",
                id: request.id,
            });
        }), (/**
         * @param {?} error
         * @return {(undefined|!Promise<void>)}
         */
        (error) => {
            if (abortController.signal.aborted) {
                return;
            }
            return this._transport?.send({
                jsonrpc: "2.0",
                id: request.id,
                error: {
                    code: Number.isSafeInteger(error["code"])
                        ? error["code"]
                        : types_1.ErrorCode.InternalError,
                    message: error.message ?? "Internal error",
                },
            });
        }))
            .catch((/**
         * @param {?} error
         * @return {void}
         */
        (error) => this._onerror(new Error(`Failed to send response: ${error}`))))
            .finally((/**
         * @return {void}
         */
        () => {
            this._requestHandlerAbortControllers.delete(request.id);
        }));
    }
    /**
     * @private
     * @param {?} notification
     * @return {void}
     */
    _onprogress(notification) {
        const { progressToken, ...params } = notification.params;
        /** @type {number} */
        const messageId = Number(progressToken);
        /** @type {(undefined|function(?): void)} */
        const handler = this._progressHandlers.get(messageId);
        if (!handler) {
            this._onerror(new Error(`Received a progress notification for an unknown token: ${JSON.stringify(notification)}`));
            return;
        }
        /** @type {(undefined|function((!Error|?)): void)} */
        const responseHandler = this._responseHandlers.get(messageId);
        /** @type {(undefined|{timeoutId: number, startTime: number, timeout: number, maxTotalTimeout: (undefined|number), resetTimeoutOnProgress: boolean, onTimeout: function(): void})} */
        const timeoutInfo = this._timeoutInfo.get(messageId);
        if (timeoutInfo && responseHandler && timeoutInfo.resetTimeoutOnProgress) {
            try {
                this._resetTimeout(messageId);
            }
            catch (error) {
                responseHandler((/** @type {!Error} */ (error)));
                return;
            }
        }
        handler(params);
    }
    /**
     * @private
     * @param {?} response
     * @return {void}
     */
    _onresponse(response) {
        /** @type {number} */
        const messageId = Number(response.id);
        /** @type {(undefined|function((!Error|?)): void)} */
        const handler = this._responseHandlers.get(messageId);
        if (handler === undefined) {
            this._onerror(new Error(`Received a response for an unknown message ID: ${JSON.stringify(response)}`));
            return;
        }
        this._responseHandlers.delete(messageId);
        this._progressHandlers.delete(messageId);
        this._cleanupTimeout(messageId);
        if ((0, types_1.isJSONRPCResponse)(response)) {
            handler(response);
        }
        else {
            /** @type {!tsickle_types_2.McpError} */
            const error = new types_1.McpError(response.error.code, response.error.message, response.error.data);
            handler(error);
        }
    }
    /**
     * @public
     * @return {(undefined|!tsickle_transport_3.Transport)}
     */
    get transport() {
        return this._transport;
    }
    /**
     * Closes the connection.
     * @public
     * @return {!Promise<void>}
     */
    async close() {
        await this._transport?.close();
    }
    /**
     * Sends a request and wait for a response.
     *
     * Do not use this method to emit notifications! Use notification() instead.
     * @public
     * @template T
     * @param {SendRequestT} request
     * @param {T} resultSchema
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    request(request, resultSchema, options) {
        const { relatedRequestId, resumptionToken, onresumptiontoken } = options ?? {};
        return new Promise((/**
         * @param {function((!PromiseLike<?>|?)): void} resolve
         * @param {function(?=): void} reject
         * @return {void}
         */
        (resolve, reject) => {
            if (!this._transport) {
                reject(new Error("Not connected"));
                return;
            }
            if (this._options?.enforceStrictCapabilities === true) {
                this.assertCapabilityForMethod(request.method);
            }
            options?.signal?.throwIfAborted();
            /** @type {number} */
            const messageId = this._requestMessageId++;
            /** @type {?} */
            const jsonrpcRequest = {
                ...request,
                jsonrpc: "2.0",
                id: messageId,
            };
            if (options?.onprogress) {
                this._progressHandlers.set(messageId, options.onprogress);
                jsonrpcRequest.params = {
                    ...request.params,
                    _meta: {
                        ...(request.params?._meta || {}),
                        progressToken: messageId
                    },
                };
            }
            /** @type {function(*): void} */
            const cancel = (/**
             * @param {*} reason
             * @return {void}
             */
            (reason) => {
                this._responseHandlers.delete(messageId);
                this._progressHandlers.delete(messageId);
                this._cleanupTimeout(messageId);
                this._transport
                    ?.send({
                    jsonrpc: "2.0",
                    method: "notifications/cancelled",
                    params: {
                        requestId: messageId,
                        reason: String(reason),
                    },
                }, { relatedRequestId, resumptionToken, onresumptiontoken })
                    .catch((/**
                 * @param {?} error
                 * @return {void}
                 */
                (error) => this._onerror(new Error(`Failed to send cancellation: ${error}`))));
                reject(reason);
            });
            this._responseHandlers.set(messageId, (/**
             * @param {(!Error|?)} response
             * @return {void}
             */
            (response) => {
                if (options?.signal?.aborted) {
                    return;
                }
                if (response instanceof Error) {
                    return reject(response);
                }
                try {
                    /** @type {!Object} */
                    const result = resultSchema.parse(response.result);
                    resolve(result);
                }
                catch (error) {
                    reject(error);
                }
            }));
            options?.signal?.addEventListener("abort", (/**
             * @return {void}
             */
            () => {
                cancel(options?.signal?.reason);
            }));
            /** @type {number} */
            const timeout = options?.timeout ?? exports.DEFAULT_REQUEST_TIMEOUT_MSEC;
            /** @type {function(): void} */
            const timeoutHandler = (/**
             * @return {void}
             */
            () => cancel(new types_1.McpError(types_1.ErrorCode.RequestTimeout, "Request timed out", { timeout })));
            this._setupTimeout(messageId, timeout, options?.maxTotalTimeout, timeoutHandler, options?.resetTimeoutOnProgress ?? false);
            this._transport.send(jsonrpcRequest, { relatedRequestId, resumptionToken, onresumptiontoken }).catch((/**
             * @param {?} error
             * @return {void}
             */
            (error) => {
                this._cleanupTimeout(messageId);
                reject(error);
            }));
        }));
    }
    /**
     * Emits a notification, which is a one-way message that does not expect a response.
     * @public
     * @param {SendNotificationT} notification
     * @param {(undefined|{relatedRequestId: (undefined|string|number)})=} options
     * @return {!Promise<void>}
     */
    async notification(notification, options) {
        if (!this._transport) {
            throw new Error("Not connected");
        }
        this.assertNotificationCapability(notification.method);
        /** @type {?} */
        const jsonrpcNotification = {
            ...notification,
            jsonrpc: "2.0",
        };
        await this._transport.send(jsonrpcNotification, options);
    }
    /**
     * Registers a handler to invoke when this protocol object receives a request with the given method.
     *
     * Note that this will replace any previous request handler for the same method.
     * @public
     * @template T
     * @param {T} requestSchema
     * @param {function(?, {signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(SendNotificationT): !Promise<void>, sendRequest: function(SendRequestT, ?, (undefined|?)=): !Promise<?>}): (SendResultT|!Promise<SendResultT>)} handler
     * @return {void}
     */
    setRequestHandler(requestSchema, handler) {
        /** @type {string} */
        const method = requestSchema.shape.method.value;
        this.assertRequestHandlerCapability(method);
        this._requestHandlers.set(method, (/**
         * @param {?} request
         * @param {{signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(SendNotificationT): !Promise<void>, sendRequest: function(SendRequestT, ?, (undefined|?)=): !Promise<?>}} extra
         * @return {!Promise<?>}
         */
        (request, extra) => {
            return Promise.resolve(handler(requestSchema.parse(request), extra));
        }));
    }
    /**
     * Removes the request handler for the given method.
     * @public
     * @param {string} method
     * @return {void}
     */
    removeRequestHandler(method) {
        this._requestHandlers.delete(method);
    }
    /**
     * Asserts that a request handler has not already been set for the given method, in preparation for a new one being automatically installed.
     * @public
     * @param {string} method
     * @return {void}
     */
    assertCanSetRequestHandler(method) {
        if (this._requestHandlers.has(method)) {
            throw new Error(`A request handler for ${method} already exists, which would be overridden`);
        }
    }
    /**
     * Registers a handler to invoke when this protocol object receives a notification with the given method.
     *
     * Note that this will replace any previous notification handler for the same method.
     * @public
     * @template T
     * @param {T} notificationSchema
     * @param {function(?): (void|!Promise<void>)} handler
     * @return {void}
     */
    setNotificationHandler(notificationSchema, handler) {
        this._notificationHandlers.set(notificationSchema.shape.method.value, (/**
         * @param {?} notification
         * @return {!Promise<void>}
         */
        (notification) => Promise.resolve(handler(notificationSchema.parse(notification)))));
    }
    /**
     * Removes the notification handler for the given method.
     * @public
     * @param {string} method
     * @return {void}
     */
    removeNotificationHandler(method) {
        this._notificationHandlers.delete(method);
    }
}
exports.Protocol = Protocol;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|!tsickle_transport_3.Transport)}
     * @private
     */
    Protocol.prototype._transport;
    /**
     * @type {number}
     * @private
     */
    Protocol.prototype._requestMessageId;
    /**
     * @type {!Map<string, function(?, {signal: !AbortSignal, authInfo: (undefined|!tsickle_types_4.AuthInfo), sessionId: (undefined|string), _meta: (undefined|?), requestId: (string|number), requestInfo: (undefined|!tsickle_types_2.RequestInfo), sendNotification: function(SendNotificationT): !Promise<void>, sendRequest: function(SendRequestT, ?, (undefined|?)=): !Promise<?>}): !Promise<SendResultT>>}
     * @private
     */
    Protocol.prototype._requestHandlers;
    /**
     * @type {!Map<(string|number), !AbortController>}
     * @private
     */
    Protocol.prototype._requestHandlerAbortControllers;
    /**
     * @type {!Map<string, function(?): !Promise<void>>}
     * @private
     */
    Protocol.prototype._notificationHandlers;
    /**
     * @type {!Map<number, function((!Error|?)): void>}
     * @private
     */
    Protocol.prototype._responseHandlers;
    /**
     * @type {!Map<number, function(?): void>}
     * @private
     */
    Protocol.prototype._progressHandlers;
    /**
     * @type {!Map<number, {timeoutId: number, startTime: number, timeout: number, maxTotalTimeout: (undefined|number), resetTimeoutOnProgress: boolean, onTimeout: function(): void}>}
     * @private
     */
    Protocol.prototype._timeoutInfo;
    /**
     * Callback for when the connection is closed for any reason.
     *
     * This is invoked when close() is called as well.
     * @type {(undefined|function(): void)}
     * @public
     */
    Protocol.prototype.onclose;
    /**
     * Callback for when an error occurs.
     *
     * Note that errors are not necessarily fatal; they are used for reporting any kind of exceptional condition out of band.
     * @type {(undefined|function(!Error): void)}
     * @public
     */
    Protocol.prototype.onerror;
    /**
     * A handler to invoke for any request types that do not have their own handler installed.
     * @type {(undefined|function(?): !Promise<SendResultT>)}
     * @public
     */
    Protocol.prototype.fallbackRequestHandler;
    /**
     * A handler to invoke for any notification types that do not have their own handler installed.
     * @type {(undefined|function(?): !Promise<void>)}
     * @public
     */
    Protocol.prototype.fallbackNotificationHandler;
    /**
     * @type {(undefined|{enforceStrictCapabilities: (undefined|boolean)})}
     * @private
     */
    Protocol.prototype._options;
    /**
     * A method to check if a capability is supported by the remote side, for the given method to be called.
     *
     * This should be implemented by subclasses.
     * @abstract
     * @protected
     * @param {?} method
     * @return {void}
     */
    Protocol.prototype.assertCapabilityForMethod = function (method) { };
    /**
     * A method to check if a notification is supported by the local side, for the given method to be sent.
     *
     * This should be implemented by subclasses.
     * @abstract
     * @protected
     * @param {?} method
     * @return {void}
     */
    Protocol.prototype.assertNotificationCapability = function (method) { };
    /**
     * A method to check if a request handler is supported by the local side, for the given method to be handled.
     *
     * This should be implemented by subclasses.
     * @abstract
     * @protected
     * @param {string} method
     * @return {void}
     */
    Protocol.prototype.assertRequestHandlerCapability = function (method) { };
}
/**
 * @template T
 * @param {T} base
 * @param {T} additional
 * @return {T}
 */
function mergeCapabilities(base, additional) {
    return Object.entries(additional).reduce((/**
     * @param {T} acc
     * @param {!Array<?>} __1
     * @return {T}
     */
    (acc, [key__tsickle_destructured_1, value__tsickle_destructured_2]) => {
        let key = /** @type {string} */ (key__tsickle_destructured_1);
        let value = /** @type {*} */ (value__tsickle_destructured_2);
        if (value && typeof value === "object") {
            acc[key] = acc[key] ? { ...acc[key], ...value } : value;
        }
        else {
            acc[key] = value;
        }
        return acc;
    }), { ...base });
}
exports.mergeCapabilities = mergeCapabilities;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2024 Anthropic, PBC
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/modelcontextprotocol/src/client/index.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.modelcontextprotocol.src.client.index');
var module = module || { id: 'third_party/javascript/modelcontextprotocol/src/client/index.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_json_schema_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.index");
const tsickle_protocol_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.shared.protocol");
const tsickle_transport_3 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.shared.transport");
const tsickle_types_4 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.types");
const tsickle_types_5 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.v3.types");
const json_schema_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.index');
const protocol_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.shared.protocol');
const types_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.types');
/** @typedef {?} */
exports.ClientOptions;
/**
 * An MCP client on top of a pluggable transport.
 *
 * The client will automatically begin the initialization flow with the server when connect() is called.
 *
 * To use with custom types, extend the base Request/Notification/Result types and pass them as type parameters:
 *
 * ```typescript
 * // Custom schemas
 * const CustomRequestSchema = RequestSchema.extend({...})
 * const CustomNotificationSchema = NotificationSchema.extend({...})
 * const CustomResultSchema = ResultSchema.extend({...})
 *
 * // Type aliases
 * type CustomRequest = z.infer<typeof CustomRequestSchema>
 * type CustomNotification = z.infer<typeof CustomNotificationSchema>
 * type CustomResult = z.infer<typeof CustomResultSchema>
 *
 * // Create typed client
 * const client = new Client<CustomRequest, CustomNotification, CustomResult>({
 *   name: "CustomClient",
 *   version: "1.0.0"
 * })
 * ```
 * @template RequestT, NotificationT, ResultT
 * @extends {tsickle_protocol_2.Protocol<(RequestT|?), (NotificationT|?), (ResultT|?)>}
 */
class Client extends protocol_1.Protocol {
    /**
     * Initializes this client with the given name and version information.
     * @public
     * @param {?} _clientInfo
     * @param {(undefined|?)=} options
     */
    constructor(_clientInfo, options) {
        super(options);
        this._clientInfo = _clientInfo;
        this._cachedToolOutputValidators = new Map();
        this._capabilities = options?.capabilities ?? {};
    }
    /**
     * Registers new capabilities. This can only be called before connecting to a transport.
     *
     * The new capabilities will be merged with any existing capabilities previously given (e.g., at initialization).
     * @public
     * @param {?} capabilities
     * @return {void}
     */
    registerCapabilities(capabilities) {
        if (this.transport) {
            throw new Error("Cannot register capabilities after connecting to transport");
        }
        this._capabilities = (0, protocol_1.mergeCapabilities)(this._capabilities, capabilities);
    }
    /**
     * @protected
     * @param {(string|number)} capability
     * @param {string} method
     * @return {void}
     */
    assertCapability(capability, method) {
        if (!this._serverCapabilities?.[capability]) {
            throw new Error(`Server does not support ${capability} (required for ${method})`);
        }
    }
    /**
     * @public
     * @param {!tsickle_transport_3.Transport} transport
     * @param {(undefined|?)=} options
     * @return {!Promise<void>}
     */
    async connect(transport, options) {
        await super.connect(transport);
        // When transport sessionId is already set this means we are trying to reconnect.
        // In this case we don't need to initialize again.
        if (transport.sessionId !== undefined) {
            return;
        }
        try {
            /** @type {?} */
            const result = await this.request({
                method: "initialize",
                params: {
                    protocolVersion: types_1.LATEST_PROTOCOL_VERSION,
                    capabilities: this._capabilities,
                    clientInfo: this._clientInfo,
                },
            }, types_1.InitializeResultSchema, options);
            if (result === undefined) {
                throw new Error(`Server sent invalid initialize result: ${result}`);
            }
            if (!types_1.SUPPORTED_PROTOCOL_VERSIONS.includes(result.protocolVersion)) {
                throw new Error(`Server's protocol version is not supported: ${result.protocolVersion}`);
            }
            this._serverCapabilities = result.capabilities;
            this._serverVersion = result.serverInfo;
            // HTTP transports must set the protocol version in each header after initialization.
            if (transport.setProtocolVersion) {
                transport.setProtocolVersion(result.protocolVersion);
            }
            this._instructions = result.instructions;
            await this.notification({
                method: "notifications/initialized",
            });
        }
        catch (error) {
            // Disconnect if initialization fails.
            void this.close();
            throw error;
        }
    }
    /**
     * After initialization has completed, this will be populated with the server's reported capabilities.
     * @public
     * @return {(undefined|?)}
     */
    getServerCapabilities() {
        return this._serverCapabilities;
    }
    /**
     * After initialization has completed, this will be populated with information about the server's name and version.
     * @public
     * @return {(undefined|?)}
     */
    getServerVersion() {
        return this._serverVersion;
    }
    /**
     * After initialization has completed, this may be populated with information about the server's instructions.
     * @public
     * @return {(undefined|string)}
     */
    getInstructions() {
        return this._instructions;
    }
    /**
     * @protected
     * @param {?} method
     * @return {void}
     */
    assertCapabilityForMethod(method) {
        switch ((/** @type {string} */ (method))) {
            case "logging/setLevel":
                if (!this._serverCapabilities?.logging) {
                    throw new Error(`Server does not support logging (required for ${method})`);
                }
                break;
            case "prompts/get":
            case "prompts/list":
                if (!this._serverCapabilities?.prompts) {
                    throw new Error(`Server does not support prompts (required for ${method})`);
                }
                break;
            case "resources/list":
            case "resources/templates/list":
            case "resources/read":
            case "resources/subscribe":
            case "resources/unsubscribe":
                if (!this._serverCapabilities?.resources) {
                    throw new Error(`Server does not support resources (required for ${method})`);
                }
                if (method === "resources/subscribe" &&
                    !this._serverCapabilities.resources.subscribe) {
                    throw new Error(`Server does not support resource subscriptions (required for ${method})`);
                }
                break;
            case "tools/call":
            case "tools/list":
                if (!this._serverCapabilities?.tools) {
                    throw new Error(`Server does not support tools (required for ${method})`);
                }
                break;
            case "completion/complete":
                if (!this._serverCapabilities?.completions) {
                    throw new Error(`Server does not support completions (required for ${method})`);
                }
                break;
            case "initialize":
                // No specific capability required for initialize
                break;
            case "ping":
                // No specific capability required for ping
                break;
        }
    }
    /**
     * @protected
     * @param {?} method
     * @return {void}
     */
    assertNotificationCapability(method) {
        switch ((/** @type {string} */ (method))) {
            case "notifications/roots/list_changed":
                if (!this._capabilities.roots?.listChanged) {
                    throw new Error(`Client does not support roots list changed notifications (required for ${method})`);
                }
                break;
            case "notifications/initialized":
                // No specific capability required for initialized
                break;
            case "notifications/cancelled":
                // Cancellation notifications are always allowed
                break;
            case "notifications/progress":
                // Progress notifications are always allowed
                break;
        }
    }
    /**
     * @protected
     * @param {string} method
     * @return {void}
     */
    assertRequestHandlerCapability(method) {
        switch (method) {
            case "sampling/createMessage":
                if (!this._capabilities.sampling) {
                    throw new Error(`Client does not support sampling capability (required for ${method})`);
                }
                break;
            case "elicitation/create":
                if (!this._capabilities.elicitation) {
                    throw new Error(`Client does not support elicitation capability (required for ${method})`);
                }
                break;
            case "roots/list":
                if (!this._capabilities.roots) {
                    throw new Error(`Client does not support roots capability (required for ${method})`);
                }
                break;
            case "ping":
                // No specific capability required for ping
                break;
        }
    }
    /**
     * @public
     * @param {(undefined|?)=} options
     * @return {!Promise<{_meta: (undefined|?)}>}
     */
    async ping(options) {
        return this.request({ method: "ping" }, types_1.EmptyResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async complete(params, options) {
        return this.request({ method: "completion/complete", params }, types_1.CompleteResultSchema, options);
    }
    /**
     * @public
     * @param {string} level
     * @param {(undefined|?)=} options
     * @return {!Promise<{_meta: (undefined|?)}>}
     */
    async setLoggingLevel(level, options) {
        return this.request({ method: "logging/setLevel", params: { level } }, types_1.EmptyResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async getPrompt(params, options) {
        return this.request({ method: "prompts/get", params }, types_1.GetPromptResultSchema, options);
    }
    /**
     * @public
     * @param {(undefined|?)=} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async listPrompts(params, options) {
        return this.request({ method: "prompts/list", params }, types_1.ListPromptsResultSchema, options);
    }
    /**
     * @public
     * @param {(undefined|?)=} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async listResources(params, options) {
        return this.request({ method: "resources/list", params }, types_1.ListResourcesResultSchema, options);
    }
    /**
     * @public
     * @param {(undefined|?)=} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async listResourceTemplates(params, options) {
        return this.request({ method: "resources/templates/list", params }, types_1.ListResourceTemplatesResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async readResource(params, options) {
        return this.request({ method: "resources/read", params }, types_1.ReadResourceResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<{_meta: (undefined|?)}>}
     */
    async subscribeResource(params, options) {
        return this.request({ method: "resources/subscribe", params }, types_1.EmptyResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<{_meta: (undefined|?)}>}
     */
    async unsubscribeResource(params, options) {
        return this.request({ method: "resources/unsubscribe", params }, types_1.EmptyResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(!tsickle_types_5.ZodObject<?, string, !tsickle_types_5.ZodSchema<?, ?, ?>, ?, ?>|!tsickle_types_5.ZodUnion<!Array<?>>)=} resultSchema
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async callTool(params, resultSchema = types_1.CallToolResultSchema, options) {
        /** @type {?} */
        const result = await this.request({ method: "tools/call", params }, resultSchema, options);
        // Check if the tool has an outputSchema
        /** @type {(undefined|!tsickle_json_schema_1.Validator)} */
        const validator = this.getToolOutputValidator(params.name);
        if (validator) {
            // If tool has outputSchema, it MUST return structuredContent (unless it's an error)
            if (!result.structuredContent && !result.isError) {
                throw new types_1.McpError(types_1.ErrorCode.InvalidRequest, `Tool ${params.name} has an output schema but did not return structured content`);
            }
            // Only validate structured content if present (not when there's an error)
            if (result.structuredContent) {
                try {
                    // Validate the structured content (which is already an object) against the schema
                    /** @type {!tsickle_json_schema_1.ValidationResult} */
                    const validationResult = validator.validate(result.structuredContent);
                    if (!validationResult.valid) {
                        /** @type {string} */
                        const errors = validationResult.errors.map((/**
                         * @param {!tsickle_json_schema_1.OutputUnit} e
                         * @return {string}
                         */
                        (e) => e.error)).join(', ');
                        throw new types_1.McpError(types_1.ErrorCode.InvalidParams, `Structured content does not match the tool's output schema: ${errors}`);
                    }
                }
                catch (error) {
                    if (error instanceof types_1.McpError) {
                        throw error;
                    }
                    throw new types_1.McpError(types_1.ErrorCode.InvalidParams, `Failed to validate structured content: ${error instanceof Error ? (/** @type {!Error} */ (error)).message : String(error)}`);
                }
            }
        }
        return result;
    }
    /**
     * @private
     * @param {!Array<?>} tools
     * @return {void}
     */
    cacheToolOutputSchemas(tools) {
        this._cachedToolOutputValidators.clear();
        for (const tool of tools) {
            // If the tool has an outputSchema, create and cache the Ajv validator
            if (tool.outputSchema) {
                try {
                    /** @type {!tsickle_json_schema_1.Validator} */
                    const validator = new json_schema_1.Validator((/** @type {!tsickle_json_schema_1.Schema} */ (tool.outputSchema)));
                    this._cachedToolOutputValidators.set(tool.name, validator);
                }
                catch {
                    // Ignore schema compilation errors
                }
            }
        }
    }
    /**
     * @private
     * @param {string} toolName
     * @return {(undefined|!tsickle_json_schema_1.Validator)}
     */
    getToolOutputValidator(toolName) {
        return this._cachedToolOutputValidators.get(toolName);
    }
    /**
     * @public
     * @param {(undefined|?)=} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async listTools(params, options) {
        /** @type {?} */
        const result = await this.request({ method: "tools/list", params }, types_1.ListToolsResultSchema, options);
        // Cache the tools and their output schemas for future validation
        this.cacheToolOutputSchemas(result.tools);
        return result;
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async sendRootsListChanged() {
        return this.notification({ method: "notifications/roots/list_changed" });
    }
}
exports.Client = Client;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|?)}
     * @private
     */
    Client.prototype._serverCapabilities;
    /**
     * @type {(undefined|?)}
     * @private
     */
    Client.prototype._serverVersion;
    /**
     * @type {?}
     * @private
     */
    Client.prototype._capabilities;
    /**
     * @type {(undefined|string)}
     * @private
     */
    Client.prototype._instructions;
    /**
     * @type {!Map<string, !tsickle_json_schema_1.Validator>}
     * @private
     */
    Client.prototype._cachedToolOutputValidators;
    /**
     * @type {?}
     * @private
     */
    Client.prototype._clientInfo;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @license
 * MIT License
 *
 * Copyright (c) 2024 Anthropic, PBC
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */
/**
 * @fileoverview added by tsickle
 * Generated from: third_party/javascript/modelcontextprotocol/src/server/index.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.third_party.javascript.modelcontextprotocol.src.server.index');
var module = module || { id: 'third_party/javascript/modelcontextprotocol/src/server/index.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_json_schema_1 = goog.requireType("google3.third_party.javascript.cfworker_json_schema.src.index");
const tsickle_protocol_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.shared.protocol");
const tsickle_types_3 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.types");
const json_schema_1 = goog.require('google3.third_party.javascript.cfworker_json_schema.src.index');
const protocol_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.shared.protocol');
const types_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.types');
/** @typedef {?} */
exports.ServerOptions;
/**
 * An MCP server on top of a pluggable transport.
 *
 * This server will automatically respond to the initialization flow as initiated from the client.
 *
 * To use with custom types, extend the base Request/Notification/Result types and pass them as type parameters:
 *
 * ```typescript
 * // Custom schemas
 * const CustomRequestSchema = RequestSchema.extend({...})
 * const CustomNotificationSchema = NotificationSchema.extend({...})
 * const CustomResultSchema = ResultSchema.extend({...})
 *
 * // Type aliases
 * type CustomRequest = z.infer<typeof CustomRequestSchema>
 * type CustomNotification = z.infer<typeof CustomNotificationSchema>
 * type CustomResult = z.infer<typeof CustomResultSchema>
 *
 * // Create typed server
 * const server = new Server<CustomRequest, CustomNotification, CustomResult>({
 *   name: "CustomServer",
 *   version: "1.0.0"
 * })
 * ```
 * @template RequestT, NotificationT, ResultT
 * @extends {tsickle_protocol_2.Protocol<(RequestT|?), (NotificationT|?), (ResultT|?)>}
 */
class Server extends protocol_1.Protocol {
    /**
     * Initializes this server with the given name and version information.
     * @public
     * @param {?} _serverInfo
     * @param {(undefined|?)=} options
     */
    constructor(_serverInfo, options) {
        super(options);
        this._serverInfo = _serverInfo;
        this._capabilities = options?.capabilities ?? {};
        this._instructions = options?.instructions;
        this.setRequestHandler(types_1.InitializeRequestSchema, (/**
         * @param {{method: string, params: ?}} request
         * @return {!Promise<?>}
         */
        (request) => this._oninitialize(request)));
        this.setNotificationHandler(types_1.InitializedNotificationSchema, (/**
         * @return {(undefined|void)}
         */
        () => this.oninitialized?.()));
    }
    /**
     * Registers new capabilities. This can only be called before connecting to a transport.
     *
     * The new capabilities will be merged with any existing capabilities previously given (e.g., at initialization).
     * @public
     * @param {?} capabilities
     * @return {void}
     */
    registerCapabilities(capabilities) {
        if (this.transport) {
            throw new Error("Cannot register capabilities after connecting to transport");
        }
        this._capabilities = (0, protocol_1.mergeCapabilities)(this._capabilities, capabilities);
    }
    /**
     * @protected
     * @param {?} method
     * @return {void}
     */
    assertCapabilityForMethod(method) {
        switch ((/** @type {string} */ (method))) {
            case "sampling/createMessage":
                if (!this._clientCapabilities?.sampling) {
                    throw new Error(`Client does not support sampling (required for ${method})`);
                }
                break;
            case "elicitation/create":
                if (!this._clientCapabilities?.elicitation) {
                    throw new Error(`Client does not support elicitation (required for ${method})`);
                }
                break;
            case "roots/list":
                if (!this._clientCapabilities?.roots) {
                    throw new Error(`Client does not support listing roots (required for ${method})`);
                }
                break;
            case "ping":
                // No specific capability required for ping
                break;
        }
    }
    /**
     * @protected
     * @param {?} method
     * @return {void}
     */
    assertNotificationCapability(method) {
        switch ((/** @type {string} */ (method))) {
            case "notifications/message":
                if (!this._capabilities.logging) {
                    throw new Error(`Server does not support logging (required for ${method})`);
                }
                break;
            case "notifications/resources/updated":
            case "notifications/resources/list_changed":
                if (!this._capabilities.resources) {
                    throw new Error(`Server does not support notifying about resources (required for ${method})`);
                }
                break;
            case "notifications/tools/list_changed":
                if (!this._capabilities.tools) {
                    throw new Error(`Server does not support notifying of tool list changes (required for ${method})`);
                }
                break;
            case "notifications/prompts/list_changed":
                if (!this._capabilities.prompts) {
                    throw new Error(`Server does not support notifying of prompt list changes (required for ${method})`);
                }
                break;
            case "notifications/cancelled":
                // Cancellation notifications are always allowed
                break;
            case "notifications/progress":
                // Progress notifications are always allowed
                break;
        }
    }
    /**
     * @protected
     * @param {string} method
     * @return {void}
     */
    assertRequestHandlerCapability(method) {
        switch (method) {
            case "sampling/createMessage":
                if (!this._capabilities.sampling) {
                    throw new Error(`Server does not support sampling (required for ${method})`);
                }
                break;
            case "logging/setLevel":
                if (!this._capabilities.logging) {
                    throw new Error(`Server does not support logging (required for ${method})`);
                }
                break;
            case "prompts/get":
            case "prompts/list":
                if (!this._capabilities.prompts) {
                    throw new Error(`Server does not support prompts (required for ${method})`);
                }
                break;
            case "resources/list":
            case "resources/templates/list":
            case "resources/read":
                if (!this._capabilities.resources) {
                    throw new Error(`Server does not support resources (required for ${method})`);
                }
                break;
            case "tools/call":
            case "tools/list":
                if (!this._capabilities.tools) {
                    throw new Error(`Server does not support tools (required for ${method})`);
                }
                break;
            case "ping":
            case "initialize":
                // No specific capability required for these methods
                break;
        }
    }
    /**
     * @private
     * @param {?} request
     * @return {!Promise<?>}
     */
    async _oninitialize(request) {
        /** @type {string} */
        const requestedVersion = request.params.protocolVersion;
        this._clientCapabilities = request.params.capabilities;
        this._clientVersion = request.params.clientInfo;
        /** @type {string} */
        const protocolVersion = types_1.SUPPORTED_PROTOCOL_VERSIONS.includes(requestedVersion)
            ? requestedVersion
            : types_1.LATEST_PROTOCOL_VERSION;
        return {
            protocolVersion,
            capabilities: this.getCapabilities(),
            serverInfo: this._serverInfo,
            ...(this._instructions && { instructions: this._instructions }),
        };
    }
    /**
     * After initialization has completed, this will be populated with the client's reported capabilities.
     * @public
     * @return {(undefined|?)}
     */
    getClientCapabilities() {
        return this._clientCapabilities;
    }
    /**
     * After initialization has completed, this will be populated with information about the client's name and version.
     * @public
     * @return {(undefined|?)}
     */
    getClientVersion() {
        return this._clientVersion;
    }
    /**
     * @private
     * @return {?}
     */
    getCapabilities() {
        return this._capabilities;
    }
    /**
     * @public
     * @return {!Promise<{_meta: (undefined|?)}>}
     */
    async ping() {
        return this.request({ method: "ping" }, types_1.EmptyResultSchema);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async createMessage(params, options) {
        return this.request({ method: "sampling/createMessage", params }, types_1.CreateMessageResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async elicitInput(params, options) {
        /** @type {?} */
        const result = await this.request({ method: "elicitation/create", params }, types_1.ElicitResultSchema, options);
        // Validate the response content against the requested schema if action is "accept"
        if (result.action === "accept" && result.content) {
            try {
                /** @type {!tsickle_json_schema_1.Validator} */
                const validator = new json_schema_1.Validator((/** @type {!tsickle_json_schema_1.Schema} */ (params.requestedSchema)));
                /** @type {!tsickle_json_schema_1.ValidationResult} */
                const validationResult = validator.validate(result.content);
                if (!validationResult.valid) {
                    /** @type {string} */
                    const errors = validationResult.errors.map((/**
                     * @param {!tsickle_json_schema_1.OutputUnit} e
                     * @return {string}
                     */
                    (e) => e.error)).join(', ');
                    throw new types_1.McpError(types_1.ErrorCode.InvalidParams, `Elicitation response content does not match requested schema: ${errors}`);
                }
            }
            catch (error) {
                if (error instanceof types_1.McpError) {
                    throw error;
                }
                throw new types_1.McpError(types_1.ErrorCode.InternalError, `Error validating elicitation response: ${error}`);
            }
        }
        return result;
    }
    /**
     * @public
     * @param {(undefined|?)=} params
     * @param {(undefined|?)=} options
     * @return {!Promise<?>}
     */
    async listRoots(params, options) {
        return this.request({ method: "roots/list", params }, types_1.ListRootsResultSchema, options);
    }
    /**
     * @public
     * @param {?} params
     * @return {!Promise<void>}
     */
    async sendLoggingMessage(params) {
        return this.notification({ method: "notifications/message", params });
    }
    /**
     * @public
     * @param {?} params
     * @return {!Promise<void>}
     */
    async sendResourceUpdated(params) {
        return this.notification({
            method: "notifications/resources/updated",
            params,
        });
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async sendResourceListChanged() {
        return this.notification({
            method: "notifications/resources/list_changed",
        });
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async sendToolListChanged() {
        return this.notification({ method: "notifications/tools/list_changed" });
    }
    /**
     * @public
     * @return {!Promise<void>}
     */
    async sendPromptListChanged() {
        return this.notification({ method: "notifications/prompts/list_changed" });
    }
}
exports.Server = Server;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|?)}
     * @private
     */
    Server.prototype._clientCapabilities;
    /**
     * @type {(undefined|?)}
     * @private
     */
    Server.prototype._clientVersion;
    /**
     * @type {?}
     * @private
     */
    Server.prototype._capabilities;
    /**
     * @type {(undefined|string)}
     * @private
     */
    Server.prototype._instructions;
    /**
     * Callback for when initialization has fully completed (i.e., the client has sent an `initialized` notification).
     * @type {(undefined|function(): void)}
     * @public
     */
    Server.prototype.oninitialized;
    /**
     * @type {?}
     * @private
     */
    Server.prototype._serverInfo;
}

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/mcp_server.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.mcp_server');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/mcp_server.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_client_1 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.client.index");
const tsickle_server_2 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.server.index");
const tsickle_types_3 = goog.requireType("google3.third_party.javascript.modelcontextprotocol.src.types");
const tsickle_child_process_4 = goog.requireType("google3.third_party.javascript.typings.node.node.child_process");
const tsickle_path_5 = goog.requireType("google3.third_party.javascript.typings.node.node.path");
const tsickle_zod_6 = goog.requireType("google3.third_party.javascript.colinhacks_zod.packages.zod.src.index");
const tsickle_stdio_transport_7 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.stdio_transport");
const tsickle_create_notebook_8 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.create_notebook");
const tsickle_delete_cell_9 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.delete_cell");
const tsickle_get_cell_outputs_10 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_cell_outputs");
const tsickle_get_notebook_info_11 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_notebook_info");
const tsickle_insert_cell_12 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.insert_cell");
const tsickle_list_cells_13 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.list_cells");
const tsickle_read_cell_14 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.read_cell");
const tsickle_replace_cell_15 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.replace_cell");
const tsickle_search_cells_16 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.search_cells");
const index_js_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.client.index');
const index_js_2 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.server.index');
const types_js_1 = goog.require('google3.third_party.javascript.modelcontextprotocol.src.types');
const child_process_1 = goog.require('google3.third_party.javascript.typings.node.node.child_process');
const path = goog.require('google3.third_party.javascript.typings.node.node.path');
const zod_1 = goog.require('google3.third_party.javascript.colinhacks_zod.packages.zod.src.index');
const stdio_transport_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.stdio_transport');
const create_notebook_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.create_notebook');
const delete_cell_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.delete_cell');
const get_cell_outputs_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_cell_outputs');
const get_notebook_info_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.get_notebook_info');
const insert_cell_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.insert_cell');
const list_cells_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.list_cells');
const read_cell_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.read_cell');
const replace_cell_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.replace_cell');
const search_cells_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.tools.search_cells');
/**
 * Basic process metadata used to walk the ancestor process tree.
 * @record
 */
function ProcessInfo() { }
exports.ProcessInfo = ProcessInfo;
/* istanbul ignore if */
if (false) {
    /**
     * @const {number}
     * @public
     */
    ProcessInfo.prototype.pid;
    /**
     * @const {number}
     * @public
     */
    ProcessInfo.prototype.ppid;
    /**
     * @const {string}
     * @public
     */
    ProcessInfo.prototype.name;
}
/**
 * Supported tool owner backends.
 * @typedef {string}
 */
exports.ToolOwner;
/**
 * Minimal interface for an MCP client used for proxying tools.
 * @record
 */
function ToolProxyClient() { }
exports.ToolProxyClient = ToolProxyClient;
/* istanbul ignore if */
if (false) {
    /**
     * @public
     * @return {!Promise<{tools: !Array<?>}>}
     */
    ToolProxyClient.prototype.listTools = function () { };
    /**
     * @public
     * @param {{name: string, arguments: (undefined|?)}} params
     * @return {!Promise<?>}
     */
    ToolProxyClient.prototype.callTool = function (params) { };
}
/**
 * Clients connected to the IDE extension's IPC sockets.
 * @record
 */
function ProxyClients() { }
exports.ProxyClients = ProxyClients;
/* istanbul ignore if */
if (false) {
    /**
     * @type {(undefined|null|!ToolProxyClient)}
     * @public
     */
    ProxyClients.prototype.notebookClient;
    /**
     * @type {(undefined|null|!ToolProxyClient)}
     * @public
     */
    ProxyClients.prototype.vizClient;
    /**
     * @type {(undefined|null|!ToolProxyClient)}
     * @public
     */
    ProxyClients.prototype.dakClient;
}
/**
 * Standalone local notebook tools exposed when not connected to an IDE.
 * @type {!Array<?>}
 */
exports.LOCAL_TOOLS = [
    {
        name: 'list_cells',
        description: 'List all cells in a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                maxLength: {
                    type: 'number',
                    description: 'Maximum length of the preview snippet for each cell (optional, defaults to 100)',
                },
            },
            required: ['notebookPath'],
        },
    },
    {
        name: 'read_cell',
        description: 'Read the content of a specific cell in a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                cellIndex: {
                    type: 'number',
                    description: '0-based index of the cell',
                },
            },
            required: ['notebookPath', 'cellIndex'],
        },
    },
    {
        name: 'insert_cell',
        description: 'Insert a new cell into a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                cellIndex: {
                    type: 'number',
                    description: 'Index at which to insert the cell (omitted to append)',
                },
                cellType: {
                    type: 'string',
                    enum: ['code', 'markdown'],
                    description: 'Type of cell',
                },
                content: { type: 'string', description: 'Content of the cell' },
            },
            required: ['notebookPath', 'cellType', 'content'],
        },
    },
    {
        name: 'replace_cell',
        description: 'Replace the content of a specific cell in a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                cellIndex: {
                    type: 'number',
                    description: '0-based index of the cell to replace',
                },
                content: { type: 'string', description: 'New content of the cell' },
            },
            required: ['notebookPath', 'cellIndex', 'content'],
        },
    },
    {
        name: 'delete_cell',
        description: 'Delete a specific cell from a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                cellIndex: {
                    type: 'number',
                    description: '0-based index of the cell to delete',
                },
            },
            required: ['notebookPath', 'cellIndex'],
        },
    },
    {
        name: 'get_notebook_info',
        description: 'Get summary information about a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
            },
            required: ['notebookPath'],
        },
    },
    {
        name: 'search_cells',
        description: 'Search for text within cells of a notebook',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                query: {
                    type: 'string',
                    description: 'Text to search for',
                },
                caseSensitive: {
                    type: 'boolean',
                    description: 'Whether search is case sensitive (optional)',
                },
            },
            required: ['notebookPath', 'query'],
        },
    },
    {
        name: 'create_notebook',
        description: 'Create a new notebook file in the workspace',
        inputSchema: {
            type: 'object',
            properties: {
                directory: {
                    type: 'string',
                    description: 'Absolute path to the directory where the notebook should be created',
                },
                filename: {
                    type: 'string',
                    description: 'Name of the notebook file (without extension)',
                },
            },
            required: ['directory', 'filename'],
        },
    },
    {
        name: 'get_cell_outputs',
        description: 'Read outputs from a code cell by index',
        inputSchema: {
            type: 'object',
            properties: {
                notebookPath: {
                    type: 'string',
                    description: 'Path to the notebook file',
                },
                cellIndex: {
                    type: 'number',
                    description: '0-based index of the cell to inspect',
                },
            },
            required: ['notebookPath', 'cellIndex'],
        },
    },
];
/** @type {!tsickle_zod_6.ZodObject<{notebookPath: !tsickle_zod_6.ZodString}, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const NotebookPathSchema = zod_1.z.object({
    notebookPath: zod_1.z.string(),
});
/** @type {!tsickle_zod_6.ZodObject<?, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const ListCellsSchema = NotebookPathSchema.extend({
    maxLength: zod_1.z.number().optional(),
});
/** @type {!tsickle_zod_6.ZodObject<?, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const CellIndexSchema = NotebookPathSchema.extend({
    cellIndex: zod_1.z.number(),
});
/** @type {!tsickle_zod_6.ZodObject<?, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const InsertCellSchema = NotebookPathSchema.extend({
    cellIndex: zod_1.z.number().optional(),
    cellType: zod_1.z.enum(['code', 'markdown']),
    content: zod_1.z.string(),
});
/** @type {!tsickle_zod_6.ZodObject<?, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const ReplaceCellSchema = CellIndexSchema.extend({
    content: zod_1.z.string(),
});
/** @type {!tsickle_zod_6.ZodObject<?, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const SearchCellsSchema = NotebookPathSchema.extend({
    query: zod_1.z.string(),
    caseSensitive: zod_1.z.boolean().optional(),
});
/** @type {!tsickle_zod_6.ZodObject<{directory: !tsickle_zod_6.ZodString, filename: !tsickle_zod_6.ZodString}, string, !tsickle_zod_6.ZodSchema<?, ?, ?>, ?, ?>} */
const CreateNotebookSchema = zod_1.z.object({
    directory: zod_1.z.string(),
    filename: zod_1.z.string(),
});
/** @type {?} */
const IDE_MAPPING = {
    'code': 'visualstudiocode',
    'code-insiders': 'visualstudiocode',
    'cursor': 'cursor',
    'antigravity': 'antigravity',
};
/**
 * Parses the `--mode=<mode>` flag from command-line arguments.
 * @param {!ReadonlyArray<string>=} argv
 * @return {(undefined|string)}
 */
function parseModeArg(argv = process.argv) {
    return argv.find((/**
     * @param {string} a
     * @return {boolean}
     */
    (a) => a.startsWith('--mode=')))?.split('=')[1];
}
exports.parseModeArg = parseModeArg;
/**
 * Returns the MCP server name corresponding to the active mode.
 * @param {(undefined|string)} mode
 * @return {string}
 */
function getServerName(mode) {
    if (mode === 'visualization') {
        return 'visualization';
    }
    if (mode === 'data-agent-kit') {
        return 'data-agent-kit';
    }
    return 'notebook';
}
exports.getServerName = getServerName;
/**
 * Parses POSIX `ps -A -o pid=,ppid=,comm=` output into process records.
 * @param {string} stdout
 * @return {!Array<!ProcessInfo>}
 */
function parsePosixPsOutput(stdout) {
    /** @type {!Array<!ProcessInfo>} */
    const processes = [];
    for (const rawLine of stdout.split('\n')) {
        /** @type {string} */
        const line = rawLine.trim();
        if (!line) {
            continue;
        }
        /** @type {(null|!RegExpExecArray)} */
        const match = /^\s*(\d+)\s+(\d+)\s+(.+)$/.exec(line);
        if (!match) {
            continue;
        }
        /** @type {number} */
        const pid = globalThis.Number(match[1]);
        /** @type {number} */
        const ppid = globalThis.Number(match[2]);
        /** @type {string} */
        const comm = match[3].trim();
        if (Number.isInteger(pid) && Number.isInteger(ppid) && comm) {
            processes.push({
                pid,
                ppid,
                name: path.basename(comm),
            });
        }
    }
    return processes;
}
exports.parsePosixPsOutput = parsePosixPsOutput;
/**
 * Parses Windows PowerShell `Get-CimInstance Win32_Process` JSON output.
 * @param {string} stdout
 * @return {!Array<!ProcessInfo>}
 */
function parseWindowsProcessJson(stdout) {
    /** @type {string} */
    const trimmed = stdout.trim();
    if (!trimmed) {
        return [];
    }
    /** @type {*} */
    const parsed = JSON.parse(trimmed);
    /** @type {!Array<*>} */
    const items = Array.isArray(parsed) ? parsed : [parsed];
    /** @type {!Array<!ProcessInfo>} */
    const processes = [];
    for (const item of items) {
        if (typeof item !== 'object' || item === null) {
            continue;
        }
        /** @type {number} */
        const pid = 'ProcessId' in item && typeof item.ProcessId === 'number'
            ? item.ProcessId
            : Number.NaN;
        /** @type {number} */
        const ppid = 'ParentProcessId' in item && typeof item.ParentProcessId === 'number'
            ? item.ParentProcessId
            : Number.NaN;
        /** @type {string} */
        const name = 'Name' in item && typeof item.Name === 'string' ? item.Name : '';
        if (Number.isInteger(pid) && Number.isInteger(ppid) && name) {
            processes.push({ pid, ppid, name });
        }
    }
    return processes;
}
exports.parseWindowsProcessJson = parseWindowsProcessJson;
/**
 * @param {string} file
 * @param {!ReadonlyArray<string>} args
 * @return {!Promise<string>}
 */
function execFileAsync(file, args) {
    return new Promise((/**
     * @param {function((string|!PromiseLike<string>)): void} resolve
     * @param {function(?=): void} reject
     * @return {void}
     */
    (resolve, reject) => {
        (0, child_process_1.execFile)(file, args, { maxBuffer: 10 * 1024 * 1024 }, (/**
         * @param {(null|?)} error
         * @param {string} stdout
         * @return {void}
         */
        (error, stdout) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout);
        }));
    }));
}
/**
 * Retrieves the running process list from the OS.
 * @return {!Promise<!Array<!ProcessInfo>>}
 */
async function getProcessList() {
    if (process.platform === 'win32') {
        /** @type {string} */
        const stdout = await execFileAsync('powershell.exe', [
            '-NoProfile',
            '-NonInteractive',
            '-Command',
            'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress',
        ]);
        return parseWindowsProcessJson(stdout);
    }
    /** @type {string} */
    const stdout = await execFileAsync('ps', ['-A', '-o', 'pid=,ppid=,comm=']);
    return parsePosixPsOutput(stdout);
}
exports.getProcessList = getProcessList;
/**
 * Walks the ancestor process tree up to 20 levels to infer the host IDE name.
 * @param {function(): !Promise<!Array<!ProcessInfo>>=} processListProvider
 * @param {number=} startPid
 * @return {!Promise<(null|string)>}
 */
async function inferIdeName(processListProvider = getProcessList, startPid = process.pid) {
    try {
        /** @type {!Array<!ProcessInfo>} */
        const processes = await processListProvider();
        /** @type {number} */
        let currentPid = startPid;
        /** @type {number} */
        let depth = 0;
        /** @type {number} */
        const maxDepth = 20;
        while (currentPid && currentPid > 1 && depth < maxDepth) {
            /** @type {(undefined|!ProcessInfo)} */
            const proc = processes.find((/**
             * @param {!ProcessInfo} p
             * @return {boolean}
             */
            (p) => p.pid === currentPid));
            if (!proc) {
                break;
            }
            /** @type {string} */
            const name = proc.name.toLowerCase();
            for (const [key__tsickle_destructured_1, mappedIde__tsickle_destructured_2] of Object.entries(IDE_MAPPING)) {
                const key = /** @type {string} */ (key__tsickle_destructured_1);
                const mappedIde = /** @type {string} */ (mappedIde__tsickle_destructured_2);
                if (name.includes(key)) {
                    return mappedIde;
                }
            }
            currentPid = proc.ppid;
            depth++;
        }
    }
    catch (error) {
        console.error('Error parsing process tree:', error);
    }
    return null;
}
exports.inferIdeName = inferIdeName;
/**
 * Creates and configures the MCP Server for the given mode and proxy clients.
 * @param {(undefined|string)} mode
 * @param {!ProxyClients=} clients
 * @return {!tsickle_server_2.Server<?, ?, ?>}
 */
function createMcpServer(mode, clients = {}) {
    /** @type {!tsickle_server_2.Server<?, ?, ?>} */
    const server = new index_js_2.Server({
        name: getServerName(mode),
        version: '0.1.0',
    }, {
        capabilities: {
            tools: {},
        },
    });
    /** @type {!Map<string, string>} */
    const toolOwnerMap = new Map();
    server.setRequestHandler(types_js_1.ListToolsRequestSchema, (/**
     * @return {!Promise<{tools: !Array<?>}>}
     */
    async () => {
        /** @type {!Array<?>} */
        const aggregatedTools = [];
        toolOwnerMap.clear();
        if (mode === 'notebook') {
            if (clients.notebookClient) {
                try {
                    /** @type {{tools: !Array<?>}} */
                    const response = await clients.notebookClient.listTools();
                    for (const t of response.tools) {
                        toolOwnerMap.set(t.name, 'notebook');
                    }
                    aggregatedTools.push(...response.tools);
                }
                catch (e) {
                    console.error('Error listing tools from notebook client:', e);
                }
            }
            else {
                for (const t of exports.LOCAL_TOOLS) {
                    toolOwnerMap.set(t.name, 'notebook');
                }
                aggregatedTools.push(...exports.LOCAL_TOOLS);
            }
        }
        if (mode === 'visualization') {
            if (clients.vizClient) {
                try {
                    /** @type {{tools: !Array<?>}} */
                    const response = await clients.vizClient.listTools();
                    for (const t of response.tools) {
                        toolOwnerMap.set(t.name, 'viz');
                    }
                    aggregatedTools.push(...response.tools);
                }
                catch (e) {
                    console.error('Error listing tools from viz client:', e);
                }
            }
        }
        if (mode === 'data-agent-kit') {
            if (clients.dakClient) {
                try {
                    /** @type {{tools: !Array<?>}} */
                    const response = await clients.dakClient.listTools();
                    for (const t of response.tools) {
                        toolOwnerMap.set(t.name, 'dak');
                    }
                    aggregatedTools.push(...response.tools);
                }
                catch (e) {
                    console.error('Error listing tools from dak client:', e);
                }
            }
        }
        return { tools: aggregatedTools };
    }));
    server.setRequestHandler(types_js_1.CallToolRequestSchema, (/**
     * @param {{method: string, params: ?}} request
     * @return {!Promise<?>}
     */
    async (request) => {
        const { name, arguments: toolArgs } = request.params;
        /** @type {(undefined|string)} */
        const owner = toolOwnerMap.get(name);
        if (owner === 'notebook' && clients.notebookClient) {
            return await clients.notebookClient.callTool({
                name,
                arguments: toolArgs,
            });
        }
        if (owner === 'viz' && clients.vizClient) {
            return await clients.vizClient.callTool({
                name,
                arguments: toolArgs,
            });
        }
        if (owner === 'dak' && clients.dakClient) {
            return await clients.dakClient.callTool({
                name,
                arguments: toolArgs,
            });
        }
        if (mode === 'visualization' && !owner) {
            throw new Error(`Tool ${name} not available in visualization mode`);
        }
        if (mode === 'data-agent-kit' && !owner) {
            throw new Error(`Tool ${name} not available in data-agent-kit mode`);
        }
        try {
            switch (name) {
                case 'list_cells': {
                    /** @type {?} */
                    const parsed = ListCellsSchema.parse(toolArgs);
                    /** @type {!tsickle_list_cells_13.ListCellsResult} */
                    const result = await (0, list_cells_1.listCells)(parsed.notebookPath, parsed.maxLength);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'read_cell': {
                    /** @type {?} */
                    const parsed = CellIndexSchema.parse(toolArgs);
                    /** @type {!tsickle_read_cell_14.ReadCellResult} */
                    const result = await (0, read_cell_1.readCell)(parsed.notebookPath, parsed.cellIndex);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'insert_cell': {
                    /** @type {?} */
                    const parsed = InsertCellSchema.parse(toolArgs);
                    /** @type {!tsickle_insert_cell_12.InsertCellResult} */
                    const result = await (0, insert_cell_1.insertCell)(parsed.notebookPath, parsed.cellType, parsed.content, parsed.cellIndex);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'replace_cell': {
                    /** @type {?} */
                    const parsed = ReplaceCellSchema.parse(toolArgs);
                    /** @type {!tsickle_replace_cell_15.ReplaceCellResult} */
                    const result = await (0, replace_cell_1.replaceCell)(parsed.notebookPath, parsed.cellIndex, parsed.content);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'delete_cell': {
                    /** @type {?} */
                    const parsed = CellIndexSchema.parse(toolArgs);
                    /** @type {!tsickle_delete_cell_9.DeleteCellResult} */
                    const result = await (0, delete_cell_1.deleteCell)(parsed.notebookPath, parsed.cellIndex);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'get_notebook_info': {
                    /** @type {?} */
                    const parsed = NotebookPathSchema.parse(toolArgs);
                    /** @type {!tsickle_get_notebook_info_11.NotebookInfoResult} */
                    const result = await (0, get_notebook_info_1.getNotebookInfo)(parsed.notebookPath);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'search_cells': {
                    /** @type {?} */
                    const parsed = SearchCellsSchema.parse(toolArgs);
                    /** @type {!tsickle_search_cells_16.SearchCellsResult} */
                    const result = await (0, search_cells_1.searchCells)(parsed.notebookPath, parsed.query, parsed.caseSensitive);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'create_notebook': {
                    /** @type {?} */
                    const parsed = CreateNotebookSchema.parse(toolArgs);
                    /** @type {!tsickle_create_notebook_8.CreateNotebookResult} */
                    const result = await (0, create_notebook_1.createNotebook)(parsed.directory, parsed.filename);
                    return {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
                    };
                }
                case 'get_cell_outputs': {
                    /** @type {?} */
                    const parsed = CellIndexSchema.parse(toolArgs);
                    /** @type {!Array<({type: string, text: string}|{type: string, data: string, mimeType: string})>} */
                    const result = await (0, get_cell_outputs_1.getCellOutputs)(parsed.notebookPath, parsed.cellIndex);
                    return {
                        content: result,
                    };
                }
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }
        }
        catch (error) {
            if (error instanceof zod_1.z.ZodError) {
                throw new Error(`Invalid arguments for ${name}: ${(/** @type {!tsickle_zod_6.ZodError<?>} */ (error)).message}`);
            }
            throw error;
        }
    }));
    return server;
}
exports.createMcpServer = createMcpServer;
/**
 * @return {?}
 */
function getCleanEnv() {
    /** @type {?} */
    const env = {};
    for (const [key__tsickle_destructured_3, value__tsickle_destructured_4] of Object.entries(process.env)) {
        const key = /** @type {string} */ (key__tsickle_destructured_3);
        const value = /** @type {(undefined|string)} */ (value__tsickle_destructured_4);
        if (value !== undefined) {
            env[key] = value;
        }
    }
    return env;
}
/**
 * @param {!tsickle_server_2.Server<?, ?, ?>} server
 * @return {!Promise<void>}
 */
async function startStandaloneServer(server) {
    /** @type {!tsickle_stdio_transport_7.StdioServerTransport} */
    const transport = new stdio_transport_1.StdioServerTransport();
    await server.connect(transport);
    console.error('Standalone Notebook MCP server running on stdio');
}
/**
 * Connects to the appropriate IDE proxy (if available) and starts the MCP server on stdio.
 * @return {!Promise<void>}
 */
async function run() {
    /** @type {(undefined|string)} */
    const mode = parseModeArg();
    /** @type {!ProxyClients} */
    const clients = {};
    /** @type {!tsickle_server_2.Server<?, ?, ?>} */
    const server = createMcpServer(mode, clients);
    /** @type {(undefined|null|string)} */
    let ideName = process.env['DATA_CLOUD_CURR_IDE_NAME'];
    if (!ideName) {
        ideName = await inferIdeName();
        if (ideName) {
            console.error(`Inferred IDE name from process tree: ${ideName}`);
        }
    }
    if (ideName) {
        /** @type {string} */
        const proxyCmd = path.resolve(__dirname, '../bin/mcp_proxy_bundle.cjs');
        /** @type {?} */
        const env = getCleanEnv();
        if (mode === 'notebook') {
            try {
                /** @type {!tsickle_stdio_transport_7.StdioClientTransport} */
                const notebookTransport = new stdio_transport_1.StdioClientTransport({
                    command: process.execPath,
                    args: [proxyCmd, `notebooks-${ideName.toLowerCase()}`],
                    env,
                });
                /** @type {!tsickle_client_1.Client<?, ?, ?>} */
                const client = new index_js_1.Client({ name: 'notebook-client', version: '0.1.0' }, { capabilities: {} });
                await client.connect(notebookTransport);
                clients.notebookClient = client;
            }
            catch {
                clients.notebookClient = null;
            }
        }
        if (mode === 'visualization') {
            try {
                /** @type {!tsickle_stdio_transport_7.StdioClientTransport} */
                const vizTransport = new stdio_transport_1.StdioClientTransport({
                    command: process.execPath,
                    args: [proxyCmd, `visualization-${ideName.toLowerCase()}`],
                    env,
                });
                /** @type {!tsickle_client_1.Client<?, ?, ?>} */
                const client = new index_js_1.Client({ name: 'viz-client', version: '0.1.0' }, { capabilities: {} });
                await client.connect(vizTransport);
                clients.vizClient = client;
            }
            catch {
                clients.vizClient = null;
            }
        }
        if (mode === 'data-agent-kit') {
            try {
                /** @type {!tsickle_stdio_transport_7.StdioClientTransport} */
                const dakTransport = new stdio_transport_1.StdioClientTransport({
                    command: process.execPath,
                    args: [proxyCmd, `dataAgentKit-${ideName.toLowerCase()}`],
                    env,
                });
                /** @type {!tsickle_client_1.Client<?, ?, ?>} */
                const client = new index_js_1.Client({ name: 'dak-client', version: '0.1.0' }, { capabilities: {} });
                await client.connect(dakTransport);
                clients.dakClient = client;
            }
            catch {
                clients.dakClient = null;
            }
        }
        if (!clients.notebookClient && !clients.vizClient && !clients.dakClient) {
            await startStandaloneServer(server);
            return;
        }
        /** @type {!tsickle_stdio_transport_7.StdioServerTransport} */
        const transport = new stdio_transport_1.StdioServerTransport();
        await server.connect(transport);
        return;
    }
    await startStandaloneServer(server);
}
exports.run = run;

;return exports;});
goog.loadModule(function(exports) {'use strict';/**
 * @fileoverview added by tsickle
 * Generated from: cloud/developer_experience/datacloud_vscode/mcp_servers/cli/mcp_server_main.ts
 * @suppress {checkTypes} added by tsickle
 * @suppress {extraRequire} added by tsickle
 * @suppress {missingRequire} added by tsickle
 * @suppress {uselessCode} added by tsickle
 * @suppress {suspiciousCode} added by tsickle
 * @suppress {missingReturn} added by tsickle
 * @suppress {unusedLocalVariables} added by tsickle
 * @suppress {missingOverride} added by tsickle
 * @suppress {const} added by tsickle
 */
goog.module('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.mcp_server_main');
var module = module || { id: 'cloud/developer_experience/datacloud_vscode/mcp_servers/cli/mcp_server_main.closure.js' };
goog.require('google3.third_party.javascript.tslib.tslib');
const tsickle_mcp_server_1 = goog.requireType("google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.mcp_server");
const mcp_server_1 = goog.require('google3.cloud.developer_experience.datacloud_vscode.mcp_servers.cli.mcp_server');
(0, mcp_server_1.run)().catch((/**
 * @param {?} error
 * @return {?}
 */
(error) => {
    console.error('Fatal error running server:', error);
    process.exit(1);
}));

;return exports;});

}.call(Object.assign(Object.create(globalThis), {"CLOSURE_NO_DEPS":true,"CLOSURE_UNCOMPILED_DEFINES":{"goog.SEAL_MODULE_EXPORTS":false}}), module.exports);

  }).call(globalThis, __req, __file, __dir, __mod, __mod.exports);
})();
