# Generated from grammar/SMEL.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMELParser import SMELParser
else:
    from SMELParser import SMELParser

# This class defines a complete generic visitor for a parse tree produced by SMELParser.

class SMELVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SMELParser#migration.
    def visitMigration(self, ctx:SMELParser.MigrationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#header.
    def visitHeader(self, ctx:SMELParser.HeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#migrationDecl.
    def visitMigrationDecl(self, ctx:SMELParser.MigrationDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#fromToDecl.
    def visitFromToDecl(self, ctx:SMELParser.FromToDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#usingDecl.
    def visitUsingDecl(self, ctx:SMELParser.UsingDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#databaseType.
    def visitDatabaseType(self, ctx:SMELParser.DatabaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#version.
    def visitVersion(self, ctx:SMELParser.VersionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#operation.
    def visitOperation(self, ctx:SMELParser.OperationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#nest.
    def visitNest(self, ctx:SMELParser.NestContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#nestClause.
    def visitNestClause(self, ctx:SMELParser.NestClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#unnest.
    def visitUnnest(self, ctx:SMELParser.UnnestContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#unnestClause.
    def visitUnnestClause(self, ctx:SMELParser.UnnestClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#flatten.
    def visitFlatten(self, ctx:SMELParser.FlattenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#flattenClause.
    def visitFlattenClause(self, ctx:SMELParser.FlattenClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#columnRenameClause.
    def visitColumnRenameClause(self, ctx:SMELParser.ColumnRenameClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withCardinalityClause.
    def visitWithCardinalityClause(self, ctx:SMELParser.WithCardinalityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#usingKeyClause.
    def visitUsingKeyClause(self, ctx:SMELParser.UsingKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#whereClause.
    def visitWhereClause(self, ctx:SMELParser.WhereClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#renameClause.
    def visitRenameClause(self, ctx:SMELParser.RenameClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#addReferenceClause.
    def visitAddReferenceClause(self, ctx:SMELParser.AddReferenceClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#generateKeyClause.
    def visitGenerateKeyClause(self, ctx:SMELParser.GenerateKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#linkingClause.
    def visitLinkingClause(self, ctx:SMELParser.LinkingClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#copy.
    def visitCopy(self, ctx:SMELParser.CopyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#move.
    def visitMove(self, ctx:SMELParser.MoveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#merge.
    def visitMerge(self, ctx:SMELParser.MergeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#split.
    def visitSplit(self, ctx:SMELParser.SplitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#cast.
    def visitCast(self, ctx:SMELParser.CastContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#linking.
    def visitLinking(self, ctx:SMELParser.LinkingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#add.
    def visitAdd(self, ctx:SMELParser.AddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#attributeAdd.
    def visitAttributeAdd(self, ctx:SMELParser.AttributeAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#attributeClause.
    def visitAttributeClause(self, ctx:SMELParser.AttributeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withTypeClause.
    def visitWithTypeClause(self, ctx:SMELParser.WithTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withDefaultClause.
    def visitWithDefaultClause(self, ctx:SMELParser.WithDefaultClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#notNullClause.
    def visitNotNullClause(self, ctx:SMELParser.NotNullClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#referenceAdd.
    def visitReferenceAdd(self, ctx:SMELParser.ReferenceAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#referenceClause.
    def visitReferenceClause(self, ctx:SMELParser.ReferenceClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#embeddedAdd.
    def visitEmbeddedAdd(self, ctx:SMELParser.EmbeddedAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#embeddedClause.
    def visitEmbeddedClause(self, ctx:SMELParser.EmbeddedClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withStructureClause.
    def visitWithStructureClause(self, ctx:SMELParser.WithStructureClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#entityAdd.
    def visitEntityAdd(self, ctx:SMELParser.EntityAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#entityClause.
    def visitEntityClause(self, ctx:SMELParser.EntityClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withKeyClause.
    def visitWithKeyClause(self, ctx:SMELParser.WithKeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#keyAdd.
    def visitKeyAdd(self, ctx:SMELParser.KeyAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#keyColumns.
    def visitKeyColumns(self, ctx:SMELParser.KeyColumnsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#variationAdd.
    def visitVariationAdd(self, ctx:SMELParser.VariationAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#relTypeAdd.
    def visitRelTypeAdd(self, ctx:SMELParser.RelTypeAddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#delete.
    def visitDelete(self, ctx:SMELParser.DeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#attributeDelete.
    def visitAttributeDelete(self, ctx:SMELParser.AttributeDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#referenceDelete.
    def visitReferenceDelete(self, ctx:SMELParser.ReferenceDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#embeddedDelete.
    def visitEmbeddedDelete(self, ctx:SMELParser.EmbeddedDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#entityDelete.
    def visitEntityDelete(self, ctx:SMELParser.EntityDeleteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#drop.
    def visitDrop(self, ctx:SMELParser.DropContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#keyDrop.
    def visitKeyDrop(self, ctx:SMELParser.KeyDropContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#variationDrop.
    def visitVariationDrop(self, ctx:SMELParser.VariationDropContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#relTypeDrop.
    def visitRelTypeDrop(self, ctx:SMELParser.RelTypeDropContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#rename.
    def visitRename(self, ctx:SMELParser.RenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#featureRename.
    def visitFeatureRename(self, ctx:SMELParser.FeatureRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#entityRename.
    def visitEntityRename(self, ctx:SMELParser.EntityRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#relTypeRename.
    def visitRelTypeRename(self, ctx:SMELParser.RelTypeRenameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#keyType.
    def visitKeyType(self, ctx:SMELParser.KeyTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#keyClause.
    def visitKeyClause(self, ctx:SMELParser.KeyClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#referencesClause.
    def visitReferencesClause(self, ctx:SMELParser.ReferencesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withColumnsClause.
    def visitWithColumnsClause(self, ctx:SMELParser.WithColumnsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#identifierList.
    def visitIdentifierList(self, ctx:SMELParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#variationClause.
    def visitVariationClause(self, ctx:SMELParser.VariationClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withAttributesClause.
    def visitWithAttributesClause(self, ctx:SMELParser.WithAttributesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withRelationshipsClause.
    def visitWithRelationshipsClause(self, ctx:SMELParser.WithRelationshipsClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withCountClause.
    def visitWithCountClause(self, ctx:SMELParser.WithCountClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#relTypeClause.
    def visitRelTypeClause(self, ctx:SMELParser.RelTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#withPropertiesClause.
    def visitWithPropertiesClause(self, ctx:SMELParser.WithPropertiesClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#extract.
    def visitExtract(self, ctx:SMELParser.ExtractContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#extractClause.
    def visitExtractClause(self, ctx:SMELParser.ExtractClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#cardinalityType.
    def visitCardinalityType(self, ctx:SMELParser.CardinalityTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#dataType.
    def visitDataType(self, ctx:SMELParser.DataTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#qualifiedName.
    def visitQualifiedName(self, ctx:SMELParser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#pathSegment.
    def visitPathSegment(self, ctx:SMELParser.PathSegmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#identifier.
    def visitIdentifier(self, ctx:SMELParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#condition.
    def visitCondition(self, ctx:SMELParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SMELParser#literal.
    def visitLiteral(self, ctx:SMELParser.LiteralContext):
        return self.visitChildren(ctx)



del SMELParser