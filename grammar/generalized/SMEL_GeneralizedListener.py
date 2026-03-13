# Generated from grammar/generalized/SMEL_Generalized.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMEL_GeneralizedParser import SMEL_GeneralizedParser
else:
    from SMEL_GeneralizedParser import SMEL_GeneralizedParser

# This class defines a complete listener for a parse tree produced by SMEL_GeneralizedParser.
class SMEL_GeneralizedListener(ParseTreeListener):

    # Enter a parse tree produced by SMEL_GeneralizedParser#migration.
    def enterMigration(self, ctx:SMEL_GeneralizedParser.MigrationContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#migration.
    def exitMigration(self, ctx:SMEL_GeneralizedParser.MigrationContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#header.
    def enterHeader(self, ctx:SMEL_GeneralizedParser.HeaderContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#header.
    def exitHeader(self, ctx:SMEL_GeneralizedParser.HeaderContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#migrationDecl.
    def enterMigrationDecl(self, ctx:SMEL_GeneralizedParser.MigrationDeclContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#migrationDecl.
    def exitMigrationDecl(self, ctx:SMEL_GeneralizedParser.MigrationDeclContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#fromToDecl.
    def enterFromToDecl(self, ctx:SMEL_GeneralizedParser.FromToDeclContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#fromToDecl.
    def exitFromToDecl(self, ctx:SMEL_GeneralizedParser.FromToDeclContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#usingDecl.
    def enterUsingDecl(self, ctx:SMEL_GeneralizedParser.UsingDeclContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#usingDecl.
    def exitUsingDecl(self, ctx:SMEL_GeneralizedParser.UsingDeclContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#databaseType.
    def enterDatabaseType(self, ctx:SMEL_GeneralizedParser.DatabaseTypeContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#databaseType.
    def exitDatabaseType(self, ctx:SMEL_GeneralizedParser.DatabaseTypeContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#version.
    def enterVersion(self, ctx:SMEL_GeneralizedParser.VersionContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#version.
    def exitVersion(self, ctx:SMEL_GeneralizedParser.VersionContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#operation.
    def enterOperation(self, ctx:SMEL_GeneralizedParser.OperationContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#operation.
    def exitOperation(self, ctx:SMEL_GeneralizedParser.OperationContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#add_gen.
    def enterAdd_gen(self, ctx:SMEL_GeneralizedParser.Add_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#add_gen.
    def exitAdd_gen(self, ctx:SMEL_GeneralizedParser.Add_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeAdd.
    def enterAttributeAdd(self, ctx:SMEL_GeneralizedParser.AttributeAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeAdd.
    def exitAttributeAdd(self, ctx:SMEL_GeneralizedParser.AttributeAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeClause.
    def enterAttributeClause(self, ctx:SMEL_GeneralizedParser.AttributeClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeClause.
    def exitAttributeClause(self, ctx:SMEL_GeneralizedParser.AttributeClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withTypeClause.
    def enterWithTypeClause(self, ctx:SMEL_GeneralizedParser.WithTypeClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withTypeClause.
    def exitWithTypeClause(self, ctx:SMEL_GeneralizedParser.WithTypeClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withDefaultClause.
    def enterWithDefaultClause(self, ctx:SMEL_GeneralizedParser.WithDefaultClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withDefaultClause.
    def exitWithDefaultClause(self, ctx:SMEL_GeneralizedParser.WithDefaultClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#notNullClause.
    def enterNotNullClause(self, ctx:SMEL_GeneralizedParser.NotNullClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#notNullClause.
    def exitNotNullClause(self, ctx:SMEL_GeneralizedParser.NotNullClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#constraintAdd.
    def enterConstraintAdd(self, ctx:SMEL_GeneralizedParser.ConstraintAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#constraintAdd.
    def exitConstraintAdd(self, ctx:SMEL_GeneralizedParser.ConstraintAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#constraintClause.
    def enterConstraintClause(self, ctx:SMEL_GeneralizedParser.ConstraintClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#constraintClause.
    def exitConstraintClause(self, ctx:SMEL_GeneralizedParser.ConstraintClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#embeddedAdd.
    def enterEmbeddedAdd(self, ctx:SMEL_GeneralizedParser.EmbeddedAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#embeddedAdd.
    def exitEmbeddedAdd(self, ctx:SMEL_GeneralizedParser.EmbeddedAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#embeddedClause.
    def enterEmbeddedClause(self, ctx:SMEL_GeneralizedParser.EmbeddedClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#embeddedClause.
    def exitEmbeddedClause(self, ctx:SMEL_GeneralizedParser.EmbeddedClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withStructureClause.
    def enterWithStructureClause(self, ctx:SMEL_GeneralizedParser.WithStructureClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withStructureClause.
    def exitWithStructureClause(self, ctx:SMEL_GeneralizedParser.WithStructureClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityAdd.
    def enterEntityAdd(self, ctx:SMEL_GeneralizedParser.EntityAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityAdd.
    def exitEntityAdd(self, ctx:SMEL_GeneralizedParser.EntityAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityClause.
    def enterEntityClause(self, ctx:SMEL_GeneralizedParser.EntityClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityClause.
    def exitEntityClause(self, ctx:SMEL_GeneralizedParser.EntityClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withKeyClause.
    def enterWithKeyClause(self, ctx:SMEL_GeneralizedParser.WithKeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withKeyClause.
    def exitWithKeyClause(self, ctx:SMEL_GeneralizedParser.WithKeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#keyAdd.
    def enterKeyAdd(self, ctx:SMEL_GeneralizedParser.KeyAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#keyAdd.
    def exitKeyAdd(self, ctx:SMEL_GeneralizedParser.KeyAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#keyColumns.
    def enterKeyColumns(self, ctx:SMEL_GeneralizedParser.KeyColumnsContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#keyColumns.
    def exitKeyColumns(self, ctx:SMEL_GeneralizedParser.KeyColumnsContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#labelAdd.
    def enterLabelAdd(self, ctx:SMEL_GeneralizedParser.LabelAddContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#labelAdd.
    def exitLabelAdd(self, ctx:SMEL_GeneralizedParser.LabelAddContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#delete_gen.
    def enterDelete_gen(self, ctx:SMEL_GeneralizedParser.Delete_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#delete_gen.
    def exitDelete_gen(self, ctx:SMEL_GeneralizedParser.Delete_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeDelete.
    def enterAttributeDelete(self, ctx:SMEL_GeneralizedParser.AttributeDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeDelete.
    def exitAttributeDelete(self, ctx:SMEL_GeneralizedParser.AttributeDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#constraintDelete.
    def enterConstraintDelete(self, ctx:SMEL_GeneralizedParser.ConstraintDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#constraintDelete.
    def exitConstraintDelete(self, ctx:SMEL_GeneralizedParser.ConstraintDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#embeddedDelete.
    def enterEmbeddedDelete(self, ctx:SMEL_GeneralizedParser.EmbeddedDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#embeddedDelete.
    def exitEmbeddedDelete(self, ctx:SMEL_GeneralizedParser.EmbeddedDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityDelete.
    def enterEntityDelete(self, ctx:SMEL_GeneralizedParser.EntityDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityDelete.
    def exitEntityDelete(self, ctx:SMEL_GeneralizedParser.EntityDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#keyDelete.
    def enterKeyDelete(self, ctx:SMEL_GeneralizedParser.KeyDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#keyDelete.
    def exitKeyDelete(self, ctx:SMEL_GeneralizedParser.KeyDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#labelDelete.
    def enterLabelDelete(self, ctx:SMEL_GeneralizedParser.LabelDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#labelDelete.
    def exitLabelDelete(self, ctx:SMEL_GeneralizedParser.LabelDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#rename_gen.
    def enterRename_gen(self, ctx:SMEL_GeneralizedParser.Rename_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#rename_gen.
    def exitRename_gen(self, ctx:SMEL_GeneralizedParser.Rename_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeRename.
    def enterAttributeRename(self, ctx:SMEL_GeneralizedParser.AttributeRenameContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeRename.
    def exitAttributeRename(self, ctx:SMEL_GeneralizedParser.AttributeRenameContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityRename.
    def enterEntityRename(self, ctx:SMEL_GeneralizedParser.EntityRenameContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityRename.
    def exitEntityRename(self, ctx:SMEL_GeneralizedParser.EntityRenameContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#keyType.
    def enterKeyType(self, ctx:SMEL_GeneralizedParser.KeyTypeContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#keyType.
    def exitKeyType(self, ctx:SMEL_GeneralizedParser.KeyTypeContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#keyClause.
    def enterKeyClause(self, ctx:SMEL_GeneralizedParser.KeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#keyClause.
    def exitKeyClause(self, ctx:SMEL_GeneralizedParser.KeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#referencesClause.
    def enterReferencesClause(self, ctx:SMEL_GeneralizedParser.ReferencesClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#referencesClause.
    def exitReferencesClause(self, ctx:SMEL_GeneralizedParser.ReferencesClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withColumnsClause.
    def enterWithColumnsClause(self, ctx:SMEL_GeneralizedParser.WithColumnsClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withColumnsClause.
    def exitWithColumnsClause(self, ctx:SMEL_GeneralizedParser.WithColumnsClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#identifierList.
    def enterIdentifierList(self, ctx:SMEL_GeneralizedParser.IdentifierListContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#identifierList.
    def exitIdentifierList(self, ctx:SMEL_GeneralizedParser.IdentifierListContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#flatten_gen.
    def enterFlatten_gen(self, ctx:SMEL_GeneralizedParser.Flatten_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#flatten_gen.
    def exitFlatten_gen(self, ctx:SMEL_GeneralizedParser.Flatten_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unflatten_gen.
    def enterUnflatten_gen(self, ctx:SMEL_GeneralizedParser.Unflatten_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unflatten_gen.
    def exitUnflatten_gen(self, ctx:SMEL_GeneralizedParser.Unflatten_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unnest_gen.
    def enterUnnest_gen(self, ctx:SMEL_GeneralizedParser.Unnest_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unnest_gen.
    def exitUnnest_gen(self, ctx:SMEL_GeneralizedParser.Unnest_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unnestCarryList.
    def enterUnnestCarryList(self, ctx:SMEL_GeneralizedParser.UnnestCarryListContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unnestCarryList.
    def exitUnnestCarryList(self, ctx:SMEL_GeneralizedParser.UnnestCarryListContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unnestCarryField.
    def enterUnnestCarryField(self, ctx:SMEL_GeneralizedParser.UnnestCarryFieldContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unnestCarryField.
    def exitUnnestCarryField(self, ctx:SMEL_GeneralizedParser.UnnestCarryFieldContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unnestFieldList.
    def enterUnnestFieldList(self, ctx:SMEL_GeneralizedParser.UnnestFieldListContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unnestFieldList.
    def exitUnnestFieldList(self, ctx:SMEL_GeneralizedParser.UnnestFieldListContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#AttributeField.
    def enterAttributeField(self, ctx:SMEL_GeneralizedParser.AttributeFieldContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#AttributeField.
    def exitAttributeField(self, ctx:SMEL_GeneralizedParser.AttributeFieldContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#NestedField.
    def enterNestedField(self, ctx:SMEL_GeneralizedParser.NestedFieldContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#NestedField.
    def exitNestedField(self, ctx:SMEL_GeneralizedParser.NestedFieldContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#unwind_gen.
    def enterUnwind_gen(self, ctx:SMEL_GeneralizedParser.Unwind_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#unwind_gen.
    def exitUnwind_gen(self, ctx:SMEL_GeneralizedParser.Unwind_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#wind_gen.
    def enterWind_gen(self, ctx:SMEL_GeneralizedParser.Wind_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#wind_gen.
    def exitWind_gen(self, ctx:SMEL_GeneralizedParser.Wind_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#nest_gen.
    def enterNest_gen(self, ctx:SMEL_GeneralizedParser.Nest_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#nest_gen.
    def exitNest_gen(self, ctx:SMEL_GeneralizedParser.Nest_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#copy_gen.
    def enterCopy_gen(self, ctx:SMEL_GeneralizedParser.Copy_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#copy_gen.
    def exitCopy_gen(self, ctx:SMEL_GeneralizedParser.Copy_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeCopy.
    def enterAttributeCopy(self, ctx:SMEL_GeneralizedParser.AttributeCopyContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeCopy.
    def exitAttributeCopy(self, ctx:SMEL_GeneralizedParser.AttributeCopyContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityCopy.
    def enterEntityCopy(self, ctx:SMEL_GeneralizedParser.EntityCopyContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityCopy.
    def exitEntityCopy(self, ctx:SMEL_GeneralizedParser.EntityCopyContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#move_gen.
    def enterMove_gen(self, ctx:SMEL_GeneralizedParser.Move_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#move_gen.
    def exitMove_gen(self, ctx:SMEL_GeneralizedParser.Move_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#merge_gen.
    def enterMerge_gen(self, ctx:SMEL_GeneralizedParser.Merge_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#merge_gen.
    def exitMerge_gen(self, ctx:SMEL_GeneralizedParser.Merge_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#split_gen.
    def enterSplit_gen(self, ctx:SMEL_GeneralizedParser.Split_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#split_gen.
    def exitSplit_gen(self, ctx:SMEL_GeneralizedParser.Split_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#splitPartGen.
    def enterSplitPartGen(self, ctx:SMEL_GeneralizedParser.SplitPartGenContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#splitPartGen.
    def exitSplitPartGen(self, ctx:SMEL_GeneralizedParser.SplitPartGenContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#cast_gen.
    def enterCast_gen(self, ctx:SMEL_GeneralizedParser.Cast_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#cast_gen.
    def exitCast_gen(self, ctx:SMEL_GeneralizedParser.Cast_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeCast.
    def enterAttributeCast(self, ctx:SMEL_GeneralizedParser.AttributeCastContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeCast.
    def exitAttributeCast(self, ctx:SMEL_GeneralizedParser.AttributeCastContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#constraintCast.
    def enterConstraintCast(self, ctx:SMEL_GeneralizedParser.ConstraintCastContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#constraintCast.
    def exitConstraintCast(self, ctx:SMEL_GeneralizedParser.ConstraintCastContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#entityCast.
    def enterEntityCast(self, ctx:SMEL_GeneralizedParser.EntityCastContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#entityCast.
    def exitEntityCast(self, ctx:SMEL_GeneralizedParser.EntityCastContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#recard_gen.
    def enterRecard_gen(self, ctx:SMEL_GeneralizedParser.Recard_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#recard_gen.
    def exitRecard_gen(self, ctx:SMEL_GeneralizedParser.Recard_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#transform_gen.
    def enterTransform_gen(self, ctx:SMEL_GeneralizedParser.Transform_genContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#transform_gen.
    def exitTransform_gen(self, ctx:SMEL_GeneralizedParser.Transform_genContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#TransformToRelationship.
    def enterTransformToRelationship(self, ctx:SMEL_GeneralizedParser.TransformToRelationshipContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#TransformToRelationship.
    def exitTransformToRelationship(self, ctx:SMEL_GeneralizedParser.TransformToRelationshipContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#TransformToEntity.
    def enterTransformToEntity(self, ctx:SMEL_GeneralizedParser.TransformToEntityContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#TransformToEntity.
    def exitTransformToEntity(self, ctx:SMEL_GeneralizedParser.TransformToEntityContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withCardinalityClause.
    def enterWithCardinalityClause(self, ctx:SMEL_GeneralizedParser.WithCardinalityClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withCardinalityClause.
    def exitWithCardinalityClause(self, ctx:SMEL_GeneralizedParser.WithCardinalityClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#usingKeyClause.
    def enterUsingKeyClause(self, ctx:SMEL_GeneralizedParser.UsingKeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#usingKeyClause.
    def exitUsingKeyClause(self, ctx:SMEL_GeneralizedParser.UsingKeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#whereClause.
    def enterWhereClause(self, ctx:SMEL_GeneralizedParser.WhereClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#whereClause.
    def exitWhereClause(self, ctx:SMEL_GeneralizedParser.WhereClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#withAttributesClause.
    def enterWithAttributesClause(self, ctx:SMEL_GeneralizedParser.WithAttributesClauseContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#withAttributesClause.
    def exitWithAttributesClause(self, ctx:SMEL_GeneralizedParser.WithAttributesClauseContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeDefList.
    def enterAttributeDefList(self, ctx:SMEL_GeneralizedParser.AttributeDefListContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeDefList.
    def exitAttributeDefList(self, ctx:SMEL_GeneralizedParser.AttributeDefListContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#attributeDef.
    def enterAttributeDef(self, ctx:SMEL_GeneralizedParser.AttributeDefContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#attributeDef.
    def exitAttributeDef(self, ctx:SMEL_GeneralizedParser.AttributeDefContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#cardinalityType.
    def enterCardinalityType(self, ctx:SMEL_GeneralizedParser.CardinalityTypeContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#cardinalityType.
    def exitCardinalityType(self, ctx:SMEL_GeneralizedParser.CardinalityTypeContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#constraintKeyType.
    def enterConstraintKeyType(self, ctx:SMEL_GeneralizedParser.ConstraintKeyTypeContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#constraintKeyType.
    def exitConstraintKeyType(self, ctx:SMEL_GeneralizedParser.ConstraintKeyTypeContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#dataType.
    def enterDataType(self, ctx:SMEL_GeneralizedParser.DataTypeContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#dataType.
    def exitDataType(self, ctx:SMEL_GeneralizedParser.DataTypeContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#qualifiedName.
    def enterQualifiedName(self, ctx:SMEL_GeneralizedParser.QualifiedNameContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#qualifiedName.
    def exitQualifiedName(self, ctx:SMEL_GeneralizedParser.QualifiedNameContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#pathSegment.
    def enterPathSegment(self, ctx:SMEL_GeneralizedParser.PathSegmentContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#pathSegment.
    def exitPathSegment(self, ctx:SMEL_GeneralizedParser.PathSegmentContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#identifier.
    def enterIdentifier(self, ctx:SMEL_GeneralizedParser.IdentifierContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#identifier.
    def exitIdentifier(self, ctx:SMEL_GeneralizedParser.IdentifierContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#condition.
    def enterCondition(self, ctx:SMEL_GeneralizedParser.ConditionContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#condition.
    def exitCondition(self, ctx:SMEL_GeneralizedParser.ConditionContext):
        pass


    # Enter a parse tree produced by SMEL_GeneralizedParser#literal.
    def enterLiteral(self, ctx:SMEL_GeneralizedParser.LiteralContext):
        pass

    # Exit a parse tree produced by SMEL_GeneralizedParser#literal.
    def exitLiteral(self, ctx:SMEL_GeneralizedParser.LiteralContext):
        pass



del SMEL_GeneralizedParser