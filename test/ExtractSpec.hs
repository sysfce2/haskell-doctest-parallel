{-# LANGUAGE ConstraintKinds #-}
{-# LANGUAGE FlexibleContexts #-}

module ExtractSpec (main, spec) where

import           Test.Hspec
import           Test.HUnit

import           GHC.Utils.Panic (GhcException (..))

import           Test.DocTest.Internal.Extract
import           Test.DocTest.Internal.Location
import           System.FilePath


shouldGive :: HasCallStack => (String, String) -> Module String -> Assertion
(d, m) `shouldGive` expected = do
  r <- fmap unLoc `fmap` extractIO ["-i" ++ dir] m
  eraseConfigLocation r `shouldBe` eraseConfigLocation expected
 where
  dir = "test/extract" </> d

main :: IO ()
main = hspec spec

spec :: Spec
spec = do
  let mod_ nm content = Module nm Nothing content []

  describe "extract" $ do
    it "extracts documentation for a top-level declaration" $ do
      ("declaration", "Foo") `shouldGive` mod_ "Foo" [" Some documentation"]

    it "extracts documentation from argument list" $ do
      ("argument-list", "Foo") `shouldGive` mod_ "Foo" [" doc for arg1", " doc for arg2"]

    it "extracts documentation for a type class function" $ do
      ("type-class", "Foo") `shouldGive` mod_ "Foo" [" Convert given value to a string."]

    it "extracts documentation from the argument list of a type class function" $ do
      ("type-class-args", "Foo") `shouldGive` mod_ "Foo" [" foo", " bar"]

    it "extracts documentation from the module header" $ do
      ("module-header", "Foo") `shouldGive` mod_ "Foo" [" Some documentation"]

    it "does not extract documentation from imported modules" $ do
      ("imported-module", "Bar") `shouldGive` mod_ "Bar" [" documentation for bar"]

    it "extracts documentation from export list" $ do
      ("export-list", "Foo") `shouldGive` mod_ "Foo" [" documentation from export list"]

    it "extracts documentation from named chunks" $ do
      ("named-chunks", "Foo") `shouldGive` mod_ "Foo" [" named chunk foo", "\n named chunk bar"]

    it "returns docstrings in the same order they appear in the source" $ do
      ("comment-order", "Foo") `shouldGive` mod_ "Foo" [" module header", " export list 1", " export list 2", " foo", " named chunk", " bar"]

    it "extracts $setup code" $ do
      ("setup", "Foo") `shouldGive` (mod_ "Foo"  [" foo", " bar", " baz"]){moduleSetup=Just "\n some setup code"}

    it "fails on invalid flags" $ do
      extractIO ["--foobar"] "test/Foo.hs" `shouldThrow` (\e -> case e of UsageError "unrecognized option `--foobar'" -> True; _ -> False)

  describe "extract (regression tests)" $ do
    it "works with infix operators" $ do
      ("regression", "Fixity") `shouldGive` mod_ "Fixity" []

    it "works with parallel list comprehensions" $ do
      ("regression", "ParallelListComp") `shouldGive` mod_ "ParallelListComp" []

    it "works with list comprehensions in instance definitions" $ do
      ("regression", "ParallelListCompClass") `shouldGive` mod_ "ParallelListCompClass" []

    it "works with foreign imports" $ do
      ("regression", "ForeignImport") `shouldGive` mod_ "ForeignImport" []

    it "works for rewrite rules" $ do
      ("regression", "RewriteRules") `shouldGive` mod_ "RewriteRules" [" doc for foo"]

    it "works for rewrite rules with type signatures" $ do
      ("regression", "RewriteRulesWithSigs") `shouldGive` mod_ "RewriteRulesWithSigs" [" doc for foo"]

    it "strips CR from dos line endings" $ do
      ("dos-line-endings", "Foo") `shouldGive` mod_ "Foo" ["\n foo\n bar\n baz"]

    it "works with a module that splices in an expression from an other module" $ do
      ("th", "Foo") `shouldGive` mod_ "Foo" [" some documentation"]

    it "works for type families and GHC 7.6.1" $ do
      ("type-families", "Foo") `shouldGive` mod_ "Foo" []

    it "ignores binder annotations" $ do
      ("module-options", "Binders") `shouldGive` mod_ "Binders" []

    it "ignores module annotations that don't start with 'doctest-parallel:'" $ do
      ("module-options", "NoOptions") `shouldGive` mod_ "NoOptions" []

    it "detects monomorphic module settings" $ do
      ("module-options", "Mono") `shouldGive` (mod_ "Mono" []){moduleConfig=
        [ noLocation "--no-randomize-error1"
        , noLocation "--no-randomize-error2"
        , noLocation "--no-randomize-error3"
        , noLocation "--no-randomize-error4"
        , noLocation "--no-randomize-error5"
        , noLocation "--no-randomize-error6"
        ]}

    it "detects polypormphic module settings" $ do
      ("module-options", "Poly") `shouldGive` (mod_ "Poly" []){moduleConfig=
        [ noLocation "--no-randomize-error"
        ]}
