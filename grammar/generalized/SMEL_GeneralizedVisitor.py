# Generated from grammar/generalized/SMEL_Generalized.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMEL_GeneralizedParser import SMEL_GeneralizedParser
else:
    from SMEL_GeneralizedParser import SMEL_GeneralizedParser

# This class defines a complete generic visitor for a parse tree produced by SMEL_GeneralizedParser.

class SMEL_GeneralizedVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SMEL_GeneralizedParser#migration.
    def visitMigration(self, ctx:SMEL_GeneralizedParser.MigrationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#header.
    def visitHeader(self, ctx:SMEL_GeneralizedParser.HeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#migrationDecl.
    def visitMigrationDecl(self, ctx:SMEL_GeneralizedParser.MigrationDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#fromToDecl.
    def visitFromToDecl(self, ctx:SMEL_GeneralizedParser.FromToDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#usingDecl.
    def visitUsingDecl(self, ctx:SMEL_GeneralizedParser.UsingDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#databaseType.
    def visitDatabaseType(self, ctx:SMEL_GeneralizedParser.DatabaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#version.
    def visitVersion(self, ctx:SMEL_GeneralizedParser.VersionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#operation.
    def visitOperation(self, ctx:SMEL_GeneralizedParser.OperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#add_gen.
    def visitAdd_gen(self, ctx:SMEL_GeneralizedParser.Add_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeAdd.
    def visitAttributeAdd(self, ctx:SMEL_GeneralizedParser.AttributeAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeClause.
    def visitAttributeClause(self, ctx:SMEL_GeneralizedParser.AttributeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withTypeClause.
    def visitWithTypeClause(self, ctx:SMEL_GeneralizedParser.WithTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withDefaultClause.
    def visitWithDefaultClause(self, ctx:SMEL_GeneralizedParser.WithDefaultClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#notNullClause.
    def visitNotNullClause(self, ctx:SMEL_GeneralizedParser.NotNullClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#constraintAdd.
    def visitConstraintAdd(self, ctx:SMEL_GeneralizedParser.ConstraintAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#constraintClause.
    def visitConstraintClause(self, ctx:SMEL_GeneralizedParser.ConstraintClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#embeddedAdd.
    def visitEmbeddedAdd(self, ctx:SMEL_GeneralizedParser.EmbeddedAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#embeddedClause.
    def visitEmbeddedClause(self, ctx:SMEL_GeneralizedParser.EmbeddedClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withStructureClause.
    def visitWithStructureClause(self, ctx:SMEL_GeneralizedParser.WithStructureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityAdd.
    def visitEntityAdd(self, ctx:SMEL_GeneralizedParser.EntityAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityClause.
    def visitEntityClause(self, ctx:SMEL_GeneralizedParser.EntityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withKeyClause.
    def visitWithKeyClause(self, ctx:SMEL_GeneralizedParser.WithKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#keyAdd.
    def visitKeyAdd(self, ctx:SMEL_GeneralizedParser.KeyAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#keyColumns.
    def visitKeyColumns(self, ctx:SMEL_GeneralizedParser.KeyColumnsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#labelAdd.
    def visitLabelAdd(self, ctx:SMEL_GeneralizedParser.LabelAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#delete_gen.
    def visitDelete_gen(self, ctx:SMEL_GeneralizedParser.Delete_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeDelete.
    def visitAttributeDelete(self, ctx:SMEL_GeneralizedParser.AttributeDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#constraintDelete.
    def visitConstraintDelete(self, ctx:SMEL_GeneralizedParser.ConstraintDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#embeddedDelete.
    def visitEmbeddedDelete(self, ctx:SMEL_GeneralizedParser.EmbeddedDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityDelete.
    def visitEntityDelete(self, ctx:SMEL_GeneralizedParser.EntityDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#keyDelete.
    def visitKeyDelete(self, ctx:SMEL_GeneralizedParser.KeyDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#labelDelete.
    def visitLabelDelete(self, ctx:SMEL_GeneralizedParser.LabelDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#rename_gen.
    def visitRename_gen(self, ctx:SMEL_GeneralizedParser.Rename_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeRename.
    def visitAttributeRename(self, ctx:SMEL_GeneralizedParser.AttributeRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityRename.
    def visitEntityRename(self, ctx:SMEL_GeneralizedParser.EntityRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#keyType.
    def visitKeyType(self, ctx:SMEL_GeneralizedParser.KeyTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#keyClause.
    def visitKeyClause(self, ctx:SMEL_GeneralizedParser.KeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#referencesClause.
    def visitReferencesClause(self, ctx:SMEL_GeneralizedParser.ReferencesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withColumnsClause.
    def visitWithColumnsClause(self, ctx:SMEL_GeneralizedParser.WithColumnsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#identifierList.
    def visitIdentifierList(self, ctx:SMEL_GeneralizedParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#flatten_gen.
    def visitFlatten_gen(self, ctx:SMEL_GeneralizedParser.Flatten_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unflatten_gen.
    def visitUnflatten_gen(self, ctx:SMEL_GeneralizedParser.Unflatten_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unnest_gen.
    def visitUnnest_gen(self, ctx:SMEL_GeneralizedParser.Unnest_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unnestCarryList.
    def visitUnnestCarryList(self, ctx:SMEL_GeneralizedParser.UnnestCarryListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unnestCarryField.
    def visitUnnestCarryField(self, ctx:SMEL_GeneralizedParser.UnnestCarryFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unnestFieldList.
    def visitUnnestFieldList(self, ctx:SMEL_GeneralizedParser.UnnestFieldListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#AttributeField.
    def visitAttributeField(self, ctx:SMEL_GeneralizedParser.AttributeFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#NestedField.
    def visitNestedField(self, ctx:SMEL_GeneralizedParser.NestedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#unwind_gen.
    def visitUnwind_gen(self, ctx:SMEL_GeneralizedParser.Unwind_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#wind_gen.
    def visitWind_gen(self, ctx:SMEL_GeneralizedParser.Wind_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#nest_gen.
    def visitNest_gen(self, ctx:SMEL_GeneralizedParser.Nest_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#copy_gen.
    def visitCopy_gen(self, ctx:SMEL_GeneralizedParser.Copy_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeCopy.
    def visitAttributeCopy(self, ctx:SMEL_GeneralizedParser.AttributeCopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityCopy.
    def visitEntityCopy(self, ctx:SMEL_GeneralizedParser.EntityCopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#move_gen.
    def visitMove_gen(self, ctx:SMEL_GeneralizedParser.Move_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#merge_gen.
    def visitMerge_gen(self, ctx:SMEL_GeneralizedParser.Merge_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#split_gen.
    def visitSplit_gen(self, ctx:SMEL_GeneralizedParser.Split_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#splitPartGen.
    def visitSplitPartGen(self, ctx:SMEL_GeneralizedParser.SplitPartGenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#cast_gen.
    def visitCast_gen(self, ctx:SMEL_GeneralizedParser.Cast_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeCast.
    def visitAttributeCast(self, ctx:SMEL_GeneralizedParser.AttributeCastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#constraintCast.
    def visitConstraintCast(self, ctx:SMEL_GeneralizedParser.ConstraintCastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#entityCast.
    def visitEntityCast(self, ctx:SMEL_GeneralizedParser.EntityCastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#recard_gen.
    def visitRecard_gen(self, ctx:SMEL_GeneralizedParser.Recard_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#transform_gen.
    def visitTransform_gen(self, ctx:SMEL_GeneralizedParser.Transform_genContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#TransformToRelationship.
    def visitTransformToRelationship(self, ctx:SMEL_GeneralizedParser.TransformToRelationshipContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#TransformToEntity.
    def visitTransformToEntity(self, ctx:SMEL_GeneralizedParser.TransformToEntityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withCardinalityClause.
    def visitWithCardinalityClause(self, ctx:SMEL_GeneralizedParser.WithCardinalityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#usingKeyClause.
    def visitUsingKeyClause(self, ctx:SMEL_GeneralizedParser.UsingKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#whereClause.
    def visitWhereClause(self, ctx:SMEL_GeneralizedParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#withAttributesClause.
    def visitWithAttributesClause(self, ctx:SMEL_GeneralizedParser.WithAttributesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeDefList.
    def visitAttributeDefList(self, ctx:SMEL_GeneralizedParser.AttributeDefListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#attributeDef.
    def visitAttributeDef(self, ctx:SMEL_GeneralizedParser.AttributeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#cardinalityType.
    def visitCardinalityType(self, ctx:SMEL_GeneralizedParser.CardinalityTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#constraintKeyType.
    def visitConstraintKeyType(self, ctx:SMEL_GeneralizedParser.ConstraintKeyTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#dataType.
    def visitDataType(self, ctx:SMEL_GeneralizedParser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#qualifiedName.
    def visitQualifiedName(self, ctx:SMEL_GeneralizedParser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#pathSegment.
    def visitPathSegment(self, ctx:SMEL_GeneralizedParser.PathSegmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#identifier.
    def visitIdentifier(self, ctx:SMEL_GeneralizedParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#condition.
    def visitCondition(self, ctx:SMEL_GeneralizedParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_GeneralizedParser#literal.
    def visitLiteral(self, ctx:SMEL_GeneralizedParser.LiteralContext):
        return self.visitChildren(ctx)



del SMEL_GeneralizedParser