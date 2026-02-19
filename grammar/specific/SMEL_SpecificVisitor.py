# Generated from grammar/SMEL_Specific.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMEL_SpecificParser import SMEL_SpecificParser
else:
    from SMEL_SpecificParser import SMEL_SpecificParser

# This class defines a complete generic visitor for a parse tree produced by SMEL_SpecificParser.

class SMEL_SpecificVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SMEL_SpecificParser#migration.
    def visitMigration(self, ctx:SMEL_SpecificParser.MigrationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#header.
    def visitHeader(self, ctx:SMEL_SpecificParser.HeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#migrationDecl.
    def visitMigrationDecl(self, ctx:SMEL_SpecificParser.MigrationDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#fromToDecl.
    def visitFromToDecl(self, ctx:SMEL_SpecificParser.FromToDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#usingDecl.
    def visitUsingDecl(self, ctx:SMEL_SpecificParser.UsingDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#databaseType.
    def visitDatabaseType(self, ctx:SMEL_SpecificParser.DatabaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#version.
    def visitVersion(self, ctx:SMEL_SpecificParser.VersionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#operation.
    def visitOperation(self, ctx:SMEL_SpecificParser.OperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_attribute.
    def visitAdd_attribute(self, ctx:SMEL_SpecificParser.Add_attributeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#attributeClause.
    def visitAttributeClause(self, ctx:SMEL_SpecificParser.AttributeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withTypeClause.
    def visitWithTypeClause(self, ctx:SMEL_SpecificParser.WithTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withDefaultClause.
    def visitWithDefaultClause(self, ctx:SMEL_SpecificParser.WithDefaultClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#notNullClause.
    def visitNotNullClause(self, ctx:SMEL_SpecificParser.NotNullClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_reference.
    def visitAdd_reference(self, ctx:SMEL_SpecificParser.Add_referenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#referenceClause.
    def visitReferenceClause(self, ctx:SMEL_SpecificParser.ReferenceClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_embedded.
    def visitAdd_embedded(self, ctx:SMEL_SpecificParser.Add_embeddedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#embeddedClause.
    def visitEmbeddedClause(self, ctx:SMEL_SpecificParser.EmbeddedClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withStructureClause.
    def visitWithStructureClause(self, ctx:SMEL_SpecificParser.WithStructureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_entity.
    def visitAdd_entity(self, ctx:SMEL_SpecificParser.Add_entityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#entityClause.
    def visitEntityClause(self, ctx:SMEL_SpecificParser.EntityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withKeyClause.
    def visitWithKeyClause(self, ctx:SMEL_SpecificParser.WithKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_primary_key.
    def visitAdd_primary_key(self, ctx:SMEL_SpecificParser.Add_primary_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_foreign_key.
    def visitAdd_foreign_key(self, ctx:SMEL_SpecificParser.Add_foreign_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_unique_key.
    def visitAdd_unique_key(self, ctx:SMEL_SpecificParser.Add_unique_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_partition_key.
    def visitAdd_partition_key(self, ctx:SMEL_SpecificParser.Add_partition_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_clustering_key.
    def visitAdd_clustering_key(self, ctx:SMEL_SpecificParser.Add_clustering_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_variation.
    def visitAdd_variation(self, ctx:SMEL_SpecificParser.Add_variationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_reltype.
    def visitAdd_reltype(self, ctx:SMEL_SpecificParser.Add_reltypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_index.
    def visitAdd_index(self, ctx:SMEL_SpecificParser.Add_indexContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#add_label.
    def visitAdd_label(self, ctx:SMEL_SpecificParser.Add_labelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#keyColumns.
    def visitKeyColumns(self, ctx:SMEL_SpecificParser.KeyColumnsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#keyClause.
    def visitKeyClause(self, ctx:SMEL_SpecificParser.KeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#referencesClause.
    def visitReferencesClause(self, ctx:SMEL_SpecificParser.ReferencesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withColumnsClause.
    def visitWithColumnsClause(self, ctx:SMEL_SpecificParser.WithColumnsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_attribute.
    def visitDelete_attribute(self, ctx:SMEL_SpecificParser.Delete_attributeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_reference.
    def visitDelete_reference(self, ctx:SMEL_SpecificParser.Delete_referenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_embedded.
    def visitDelete_embedded(self, ctx:SMEL_SpecificParser.Delete_embeddedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_entity.
    def visitDelete_entity(self, ctx:SMEL_SpecificParser.Delete_entityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_primary_key.
    def visitDelete_primary_key(self, ctx:SMEL_SpecificParser.Delete_primary_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_foreign_key.
    def visitDelete_foreign_key(self, ctx:SMEL_SpecificParser.Delete_foreign_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_unique_key.
    def visitDelete_unique_key(self, ctx:SMEL_SpecificParser.Delete_unique_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_partition_key.
    def visitDelete_partition_key(self, ctx:SMEL_SpecificParser.Delete_partition_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_clustering_key.
    def visitDelete_clustering_key(self, ctx:SMEL_SpecificParser.Delete_clustering_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_variation.
    def visitDelete_variation(self, ctx:SMEL_SpecificParser.Delete_variationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_reltype.
    def visitDelete_reltype(self, ctx:SMEL_SpecificParser.Delete_reltypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_index.
    def visitDelete_index(self, ctx:SMEL_SpecificParser.Delete_indexContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#delete_label.
    def visitDelete_label(self, ctx:SMEL_SpecificParser.Delete_labelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#remove_index.
    def visitRemove_index(self, ctx:SMEL_SpecificParser.Remove_indexContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#remove_unique_key.
    def visitRemove_unique_key(self, ctx:SMEL_SpecificParser.Remove_unique_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#remove_foreign_key.
    def visitRemove_foreign_key(self, ctx:SMEL_SpecificParser.Remove_foreign_keyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#remove_label.
    def visitRemove_label(self, ctx:SMEL_SpecificParser.Remove_labelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#remove_variation.
    def visitRemove_variation(self, ctx:SMEL_SpecificParser.Remove_variationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#rename_attribute.
    def visitRename_attribute(self, ctx:SMEL_SpecificParser.Rename_attributeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#rename_entity.
    def visitRename_entity(self, ctx:SMEL_SpecificParser.Rename_entityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#rename_reltype.
    def visitRename_reltype(self, ctx:SMEL_SpecificParser.Rename_reltypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#flatten.
    def visitFlatten(self, ctx:SMEL_SpecificParser.FlattenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unflatten.
    def visitUnflatten(self, ctx:SMEL_SpecificParser.UnflattenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unnest.
    def visitUnnest(self, ctx:SMEL_SpecificParser.UnnestContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unnestCarryList.
    def visitUnnestCarryList(self, ctx:SMEL_SpecificParser.UnnestCarryListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unnestCarryField.
    def visitUnnestCarryField(self, ctx:SMEL_SpecificParser.UnnestCarryFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unnestFieldList.
    def visitUnnestFieldList(self, ctx:SMEL_SpecificParser.UnnestFieldListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#AttributeField.
    def visitAttributeField(self, ctx:SMEL_SpecificParser.AttributeFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#NestedField.
    def visitNestedField(self, ctx:SMEL_SpecificParser.NestedFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#unwind.
    def visitUnwind(self, ctx:SMEL_SpecificParser.UnwindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#wind.
    def visitWind(self, ctx:SMEL_SpecificParser.WindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#nest.
    def visitNest(self, ctx:SMEL_SpecificParser.NestContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#copy.
    def visitCopy(self, ctx:SMEL_SpecificParser.CopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#move.
    def visitMove(self, ctx:SMEL_SpecificParser.MoveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#merge.
    def visitMerge(self, ctx:SMEL_SpecificParser.MergeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#split.
    def visitSplit(self, ctx:SMEL_SpecificParser.SplitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#splitPart.
    def visitSplitPart(self, ctx:SMEL_SpecificParser.SplitPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#cast.
    def visitCast(self, ctx:SMEL_SpecificParser.CastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#linking.
    def visitLinking(self, ctx:SMEL_SpecificParser.LinkingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withCardinalityClause.
    def visitWithCardinalityClause(self, ctx:SMEL_SpecificParser.WithCardinalityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#usingKeyClause.
    def visitUsingKeyClause(self, ctx:SMEL_SpecificParser.UsingKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#whereClause.
    def visitWhereClause(self, ctx:SMEL_SpecificParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#variationClause.
    def visitVariationClause(self, ctx:SMEL_SpecificParser.VariationClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withAttributesClause.
    def visitWithAttributesClause(self, ctx:SMEL_SpecificParser.WithAttributesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withRelationshipsClause.
    def visitWithRelationshipsClause(self, ctx:SMEL_SpecificParser.WithRelationshipsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withCountClause.
    def visitWithCountClause(self, ctx:SMEL_SpecificParser.WithCountClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#relTypeClause.
    def visitRelTypeClause(self, ctx:SMEL_SpecificParser.RelTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#withPropertiesClause.
    def visitWithPropertiesClause(self, ctx:SMEL_SpecificParser.WithPropertiesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#identifierList.
    def visitIdentifierList(self, ctx:SMEL_SpecificParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#cardinalityType.
    def visitCardinalityType(self, ctx:SMEL_SpecificParser.CardinalityTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#dataType.
    def visitDataType(self, ctx:SMEL_SpecificParser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#qualifiedName.
    def visitQualifiedName(self, ctx:SMEL_SpecificParser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#pathSegment.
    def visitPathSegment(self, ctx:SMEL_SpecificParser.PathSegmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#identifier.
    def visitIdentifier(self, ctx:SMEL_SpecificParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#condition.
    def visitCondition(self, ctx:SMEL_SpecificParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMEL_SpecificParser#literal.
    def visitLiteral(self, ctx:SMEL_SpecificParser.LiteralContext):
        return self.visitChildren(ctx)



del SMEL_SpecificParser