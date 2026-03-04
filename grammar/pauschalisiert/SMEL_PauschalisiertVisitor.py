# Generated from grammar/SMEL_Pauschalisiert.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMEL_PauschalisiertParser import SMEL_PauschalisiertParser
else:
    from SMEL_PauschalisiertParser import SMEL_PauschalisiertParser

# This class defines a complete generic visitor for a parse tree produced by SMEL_PauschalisiertParser.

class SMEL_PauschalisiertVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SMEL_PauschalisiertParser#migration.
    def visitMigration(self, ctx:SMEL_PauschalisiertParser.MigrationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#header.
    def visitHeader(self, ctx:SMEL_PauschalisiertParser.HeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#migrationDecl.
    def visitMigrationDecl(self, ctx:SMEL_PauschalisiertParser.MigrationDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#fromToDecl.
    def visitFromToDecl(self, ctx:SMEL_PauschalisiertParser.FromToDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#usingDecl.
    def visitUsingDecl(self, ctx:SMEL_PauschalisiertParser.UsingDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#databaseType.
    def visitDatabaseType(self, ctx:SMEL_PauschalisiertParser.DatabaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#version.
    def visitVersion(self, ctx:SMEL_PauschalisiertParser.VersionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#operation.
    def visitOperation(self, ctx:SMEL_PauschalisiertParser.OperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#add_ps.
    def visitAdd_ps(self, ctx:SMEL_PauschalisiertParser.Add_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeAdd.
    def visitAttributeAdd(self, ctx:SMEL_PauschalisiertParser.AttributeAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeClause.
    def visitAttributeClause(self, ctx:SMEL_PauschalisiertParser.AttributeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withTypeClause.
    def visitWithTypeClause(self, ctx:SMEL_PauschalisiertParser.WithTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withDefaultClause.
    def visitWithDefaultClause(self, ctx:SMEL_PauschalisiertParser.WithDefaultClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#notNullClause.
    def visitNotNullClause(self, ctx:SMEL_PauschalisiertParser.NotNullClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#constraintAdd.
    def visitConstraintAdd(self, ctx:SMEL_PauschalisiertParser.ConstraintAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#constraintClause.
    def visitConstraintClause(self, ctx:SMEL_PauschalisiertParser.ConstraintClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#embeddedAdd.
    def visitEmbeddedAdd(self, ctx:SMEL_PauschalisiertParser.EmbeddedAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#embeddedClause.
    def visitEmbeddedClause(self, ctx:SMEL_PauschalisiertParser.EmbeddedClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withStructureClause.
    def visitWithStructureClause(self, ctx:SMEL_PauschalisiertParser.WithStructureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#entityAdd.
    def visitEntityAdd(self, ctx:SMEL_PauschalisiertParser.EntityAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#entityClause.
    def visitEntityClause(self, ctx:SMEL_PauschalisiertParser.EntityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withKeyClause.
    def visitWithKeyClause(self, ctx:SMEL_PauschalisiertParser.WithKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#keyAdd.
    def visitKeyAdd(self, ctx:SMEL_PauschalisiertParser.KeyAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#keyColumns.
    def visitKeyColumns(self, ctx:SMEL_PauschalisiertParser.KeyColumnsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#labelAdd.
    def visitLabelAdd(self, ctx:SMEL_PauschalisiertParser.LabelAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#reltypeAdd.
    def visitReltypeAdd(self, ctx:SMEL_PauschalisiertParser.ReltypeAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#delete_ps.
    def visitDelete_ps(self, ctx:SMEL_PauschalisiertParser.Delete_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeDelete.
    def visitAttributeDelete(self, ctx:SMEL_PauschalisiertParser.AttributeDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#constraintDelete.
    def visitConstraintDelete(self, ctx:SMEL_PauschalisiertParser.ConstraintDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#embeddedDelete.
    def visitEmbeddedDelete(self, ctx:SMEL_PauschalisiertParser.EmbeddedDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#entityDelete.
    def visitEntityDelete(self, ctx:SMEL_PauschalisiertParser.EntityDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#keyDelete.
    def visitKeyDelete(self, ctx:SMEL_PauschalisiertParser.KeyDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#labelDelete.
    def visitLabelDelete(self, ctx:SMEL_PauschalisiertParser.LabelDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#reltypeDelete.
    def visitReltypeDelete(self, ctx:SMEL_PauschalisiertParser.ReltypeDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#remove_ps.
    def visitRemove_ps(self, ctx:SMEL_PauschalisiertParser.Remove_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#uniqueKeyRemove.
    def visitUniqueKeyRemove(self, ctx:SMEL_PauschalisiertParser.UniqueKeyRemoveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#foreignKeyRemove.
    def visitForeignKeyRemove(self, ctx:SMEL_PauschalisiertParser.ForeignKeyRemoveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#labelRemove.
    def visitLabelRemove(self, ctx:SMEL_PauschalisiertParser.LabelRemoveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#rename_ps.
    def visitRename_ps(self, ctx:SMEL_PauschalisiertParser.Rename_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeRename.
    def visitAttributeRename(self, ctx:SMEL_PauschalisiertParser.AttributeRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#entityRename.
    def visitEntityRename(self, ctx:SMEL_PauschalisiertParser.EntityRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#reltypeRename.
    def visitReltypeRename(self, ctx:SMEL_PauschalisiertParser.ReltypeRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#keyType.
    def visitKeyType(self, ctx:SMEL_PauschalisiertParser.KeyTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#keyClause.
    def visitKeyClause(self, ctx:SMEL_PauschalisiertParser.KeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#referencesClause.
    def visitReferencesClause(self, ctx:SMEL_PauschalisiertParser.ReferencesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withColumnsClause.
    def visitWithColumnsClause(self, ctx:SMEL_PauschalisiertParser.WithColumnsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#identifierList.
    def visitIdentifierList(self, ctx:SMEL_PauschalisiertParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#flatten_ps.
    def visitFlatten_ps(self, ctx:SMEL_PauschalisiertParser.Flatten_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unflatten_ps.
    def visitUnflatten_ps(self, ctx:SMEL_PauschalisiertParser.Unflatten_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unnest_ps.
    def visitUnnest_ps(self, ctx:SMEL_PauschalisiertParser.Unnest_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unnestCarryList.
    def visitUnnestCarryList(self, ctx:SMEL_PauschalisiertParser.UnnestCarryListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unnestCarryField.
    def visitUnnestCarryField(self, ctx:SMEL_PauschalisiertParser.UnnestCarryFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unnestFieldList.
    def visitUnnestFieldList(self, ctx:SMEL_PauschalisiertParser.UnnestFieldListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#AttributeField.
    def visitAttributeField(self, ctx:SMEL_PauschalisiertParser.AttributeFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#NestedField.
    def visitNestedField(self, ctx:SMEL_PauschalisiertParser.NestedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#unwind_ps.
    def visitUnwind_ps(self, ctx:SMEL_PauschalisiertParser.Unwind_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#wind_ps.
    def visitWind_ps(self, ctx:SMEL_PauschalisiertParser.Wind_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#nest_ps.
    def visitNest_ps(self, ctx:SMEL_PauschalisiertParser.Nest_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#copy_ps.
    def visitCopy_ps(self, ctx:SMEL_PauschalisiertParser.Copy_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeCopy.
    def visitAttributeCopy(self, ctx:SMEL_PauschalisiertParser.AttributeCopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#entityCopy.
    def visitEntityCopy(self, ctx:SMEL_PauschalisiertParser.EntityCopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#move_ps.
    def visitMove_ps(self, ctx:SMEL_PauschalisiertParser.Move_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#merge_ps.
    def visitMerge_ps(self, ctx:SMEL_PauschalisiertParser.Merge_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#split_ps.
    def visitSplit_ps(self, ctx:SMEL_PauschalisiertParser.Split_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#splitPartPs.
    def visitSplitPartPs(self, ctx:SMEL_PauschalisiertParser.SplitPartPsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#cast_ps.
    def visitCast_ps(self, ctx:SMEL_PauschalisiertParser.Cast_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#attributeCast.
    def visitAttributeCast(self, ctx:SMEL_PauschalisiertParser.AttributeCastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#constraintCast.
    def visitConstraintCast(self, ctx:SMEL_PauschalisiertParser.ConstraintCastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#recard_ps.
    def visitRecard_ps(self, ctx:SMEL_PauschalisiertParser.Recard_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#transform_ps.
    def visitTransform_ps(self, ctx:SMEL_PauschalisiertParser.Transform_psContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#TransformToRelationship.
    def visitTransformToRelationship(self, ctx:SMEL_PauschalisiertParser.TransformToRelationshipContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#TransformToEntity.
    def visitTransformToEntity(self, ctx:SMEL_PauschalisiertParser.TransformToEntityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withCardinalityClause.
    def visitWithCardinalityClause(self, ctx:SMEL_PauschalisiertParser.WithCardinalityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#usingKeyClause.
    def visitUsingKeyClause(self, ctx:SMEL_PauschalisiertParser.UsingKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#whereClause.
    def visitWhereClause(self, ctx:SMEL_PauschalisiertParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#withAttributesClause.
    def visitWithAttributesClause(self, ctx:SMEL_PauschalisiertParser.WithAttributesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#cardinalityType.
    def visitCardinalityType(self, ctx:SMEL_PauschalisiertParser.CardinalityTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#constraintKeyType.
    def visitConstraintKeyType(self, ctx:SMEL_PauschalisiertParser.ConstraintKeyTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#dataType.
    def visitDataType(self, ctx:SMEL_PauschalisiertParser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#qualifiedName.
    def visitQualifiedName(self, ctx:SMEL_PauschalisiertParser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#pathSegment.
    def visitPathSegment(self, ctx:SMEL_PauschalisiertParser.PathSegmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#identifier.
    def visitIdentifier(self, ctx:SMEL_PauschalisiertParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#condition.
    def visitCondition(self, ctx:SMEL_PauschalisiertParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_PauschalisiertParser#literal.
    def visitLiteral(self, ctx:SMEL_PauschalisiertParser.LiteralContext):
        return self.visitChildren(ctx)



del SMEL_PauschalisiertParser