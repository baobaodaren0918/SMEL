# Generated from grammar/SMEL.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMELParser import SMELParser
else:
    from SMELParser import SMELParser

# This class defines a complete listener for a parse tree produced by SMELParser.
class SMELListener(ParseTreeListener):

    # Enter a parse tree produced by SMELParser#migration.
    def enterMigration(self, ctx:SMELParser.MigrationContext):
        pass

    # Exit a parse tree produced by SMELParser#migration.
    def exitMigration(self, ctx:SMELParser.MigrationContext):
        pass


    # Enter a parse tree produced by SMELParser#header.
    def enterHeader(self, ctx:SMELParser.HeaderContext):
        pass

    # Exit a parse tree produced by SMELParser#header.
    def exitHeader(self, ctx:SMELParser.HeaderContext):
        pass


    # Enter a parse tree produced by SMELParser#migrationDecl.
    def enterMigrationDecl(self, ctx:SMELParser.MigrationDeclContext):
        pass

    # Exit a parse tree produced by SMELParser#migrationDecl.
    def exitMigrationDecl(self, ctx:SMELParser.MigrationDeclContext):
        pass


    # Enter a parse tree produced by SMELParser#fromToDecl.
    def enterFromToDecl(self, ctx:SMELParser.FromToDeclContext):
        pass

    # Exit a parse tree produced by SMELParser#fromToDecl.
    def exitFromToDecl(self, ctx:SMELParser.FromToDeclContext):
        pass


    # Enter a parse tree produced by SMELParser#usingDecl.
    def enterUsingDecl(self, ctx:SMELParser.UsingDeclContext):
        pass

    # Exit a parse tree produced by SMELParser#usingDecl.
    def exitUsingDecl(self, ctx:SMELParser.UsingDeclContext):
        pass


    # Enter a parse tree produced by SMELParser#databaseType.
    def enterDatabaseType(self, ctx:SMELParser.DatabaseTypeContext):
        pass

    # Exit a parse tree produced by SMELParser#databaseType.
    def exitDatabaseType(self, ctx:SMELParser.DatabaseTypeContext):
        pass


    # Enter a parse tree produced by SMELParser#version.
    def enterVersion(self, ctx:SMELParser.VersionContext):
        pass

    # Exit a parse tree produced by SMELParser#version.
    def exitVersion(self, ctx:SMELParser.VersionContext):
        pass


    # Enter a parse tree produced by SMELParser#operation.
    def enterOperation(self, ctx:SMELParser.OperationContext):
        pass

    # Exit a parse tree produced by SMELParser#operation.
    def exitOperation(self, ctx:SMELParser.OperationContext):
        pass


    # Enter a parse tree produced by SMELParser#nest.
    def enterNest(self, ctx:SMELParser.NestContext):
        pass

    # Exit a parse tree produced by SMELParser#nest.
    def exitNest(self, ctx:SMELParser.NestContext):
        pass


    # Enter a parse tree produced by SMELParser#nestClause.
    def enterNestClause(self, ctx:SMELParser.NestClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#nestClause.
    def exitNestClause(self, ctx:SMELParser.NestClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#unnest.
    def enterUnnest(self, ctx:SMELParser.UnnestContext):
        pass

    # Exit a parse tree produced by SMELParser#unnest.
    def exitUnnest(self, ctx:SMELParser.UnnestContext):
        pass


    # Enter a parse tree produced by SMELParser#unnestClause.
    def enterUnnestClause(self, ctx:SMELParser.UnnestClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#unnestClause.
    def exitUnnestClause(self, ctx:SMELParser.UnnestClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#flatten.
    def enterFlatten(self, ctx:SMELParser.FlattenContext):
        pass

    # Exit a parse tree produced by SMELParser#flatten.
    def exitFlatten(self, ctx:SMELParser.FlattenContext):
        pass


    # Enter a parse tree produced by SMELParser#flattenClause.
    def enterFlattenClause(self, ctx:SMELParser.FlattenClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#flattenClause.
    def exitFlattenClause(self, ctx:SMELParser.FlattenClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#columnRenameClause.
    def enterColumnRenameClause(self, ctx:SMELParser.ColumnRenameClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#columnRenameClause.
    def exitColumnRenameClause(self, ctx:SMELParser.ColumnRenameClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withCardinalityClause.
    def enterWithCardinalityClause(self, ctx:SMELParser.WithCardinalityClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withCardinalityClause.
    def exitWithCardinalityClause(self, ctx:SMELParser.WithCardinalityClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#usingKeyClause.
    def enterUsingKeyClause(self, ctx:SMELParser.UsingKeyClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#usingKeyClause.
    def exitUsingKeyClause(self, ctx:SMELParser.UsingKeyClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#whereClause.
    def enterWhereClause(self, ctx:SMELParser.WhereClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#whereClause.
    def exitWhereClause(self, ctx:SMELParser.WhereClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#renameClause.
    def enterRenameClause(self, ctx:SMELParser.RenameClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#renameClause.
    def exitRenameClause(self, ctx:SMELParser.RenameClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#addReferenceClause.
    def enterAddReferenceClause(self, ctx:SMELParser.AddReferenceClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#addReferenceClause.
    def exitAddReferenceClause(self, ctx:SMELParser.AddReferenceClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#generateKeyClause.
    def enterGenerateKeyClause(self, ctx:SMELParser.GenerateKeyClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#generateKeyClause.
    def exitGenerateKeyClause(self, ctx:SMELParser.GenerateKeyClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#linkingClause.
    def enterLinkingClause(self, ctx:SMELParser.LinkingClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#linkingClause.
    def exitLinkingClause(self, ctx:SMELParser.LinkingClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#copy.
    def enterCopy(self, ctx:SMELParser.CopyContext):
        pass

    # Exit a parse tree produced by SMELParser#copy.
    def exitCopy(self, ctx:SMELParser.CopyContext):
        pass


    # Enter a parse tree produced by SMELParser#move.
    def enterMove(self, ctx:SMELParser.MoveContext):
        pass

    # Exit a parse tree produced by SMELParser#move.
    def exitMove(self, ctx:SMELParser.MoveContext):
        pass


    # Enter a parse tree produced by SMELParser#merge.
    def enterMerge(self, ctx:SMELParser.MergeContext):
        pass

    # Exit a parse tree produced by SMELParser#merge.
    def exitMerge(self, ctx:SMELParser.MergeContext):
        pass


    # Enter a parse tree produced by SMELParser#split.
    def enterSplit(self, ctx:SMELParser.SplitContext):
        pass

    # Exit a parse tree produced by SMELParser#split.
    def exitSplit(self, ctx:SMELParser.SplitContext):
        pass


    # Enter a parse tree produced by SMELParser#cast.
    def enterCast(self, ctx:SMELParser.CastContext):
        pass

    # Exit a parse tree produced by SMELParser#cast.
    def exitCast(self, ctx:SMELParser.CastContext):
        pass


    # Enter a parse tree produced by SMELParser#linking.
    def enterLinking(self, ctx:SMELParser.LinkingContext):
        pass

    # Exit a parse tree produced by SMELParser#linking.
    def exitLinking(self, ctx:SMELParser.LinkingContext):
        pass


    # Enter a parse tree produced by SMELParser#add.
    def enterAdd(self, ctx:SMELParser.AddContext):
        pass

    # Exit a parse tree produced by SMELParser#add.
    def exitAdd(self, ctx:SMELParser.AddContext):
        pass


    # Enter a parse tree produced by SMELParser#attributeAdd.
    def enterAttributeAdd(self, ctx:SMELParser.AttributeAddContext):
        pass

    # Exit a parse tree produced by SMELParser#attributeAdd.
    def exitAttributeAdd(self, ctx:SMELParser.AttributeAddContext):
        pass


    # Enter a parse tree produced by SMELParser#attributeClause.
    def enterAttributeClause(self, ctx:SMELParser.AttributeClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#attributeClause.
    def exitAttributeClause(self, ctx:SMELParser.AttributeClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withTypeClause.
    def enterWithTypeClause(self, ctx:SMELParser.WithTypeClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withTypeClause.
    def exitWithTypeClause(self, ctx:SMELParser.WithTypeClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withDefaultClause.
    def enterWithDefaultClause(self, ctx:SMELParser.WithDefaultClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withDefaultClause.
    def exitWithDefaultClause(self, ctx:SMELParser.WithDefaultClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#notNullClause.
    def enterNotNullClause(self, ctx:SMELParser.NotNullClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#notNullClause.
    def exitNotNullClause(self, ctx:SMELParser.NotNullClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#referenceAdd.
    def enterReferenceAdd(self, ctx:SMELParser.ReferenceAddContext):
        pass

    # Exit a parse tree produced by SMELParser#referenceAdd.
    def exitReferenceAdd(self, ctx:SMELParser.ReferenceAddContext):
        pass


    # Enter a parse tree produced by SMELParser#referenceClause.
    def enterReferenceClause(self, ctx:SMELParser.ReferenceClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#referenceClause.
    def exitReferenceClause(self, ctx:SMELParser.ReferenceClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#embeddedAdd.
    def enterEmbeddedAdd(self, ctx:SMELParser.EmbeddedAddContext):
        pass

    # Exit a parse tree produced by SMELParser#embeddedAdd.
    def exitEmbeddedAdd(self, ctx:SMELParser.EmbeddedAddContext):
        pass


    # Enter a parse tree produced by SMELParser#embeddedClause.
    def enterEmbeddedClause(self, ctx:SMELParser.EmbeddedClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#embeddedClause.
    def exitEmbeddedClause(self, ctx:SMELParser.EmbeddedClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withStructureClause.
    def enterWithStructureClause(self, ctx:SMELParser.WithStructureClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withStructureClause.
    def exitWithStructureClause(self, ctx:SMELParser.WithStructureClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#entityAdd.
    def enterEntityAdd(self, ctx:SMELParser.EntityAddContext):
        pass

    # Exit a parse tree produced by SMELParser#entityAdd.
    def exitEntityAdd(self, ctx:SMELParser.EntityAddContext):
        pass


    # Enter a parse tree produced by SMELParser#entityClause.
    def enterEntityClause(self, ctx:SMELParser.EntityClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#entityClause.
    def exitEntityClause(self, ctx:SMELParser.EntityClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withKeyClause.
    def enterWithKeyClause(self, ctx:SMELParser.WithKeyClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withKeyClause.
    def exitWithKeyClause(self, ctx:SMELParser.WithKeyClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#keyAdd.
    def enterKeyAdd(self, ctx:SMELParser.KeyAddContext):
        pass

    # Exit a parse tree produced by SMELParser#keyAdd.
    def exitKeyAdd(self, ctx:SMELParser.KeyAddContext):
        pass


    # Enter a parse tree produced by SMELParser#keyColumns.
    def enterKeyColumns(self, ctx:SMELParser.KeyColumnsContext):
        pass

    # Exit a parse tree produced by SMELParser#keyColumns.
    def exitKeyColumns(self, ctx:SMELParser.KeyColumnsContext):
        pass


    # Enter a parse tree produced by SMELParser#variationAdd.
    def enterVariationAdd(self, ctx:SMELParser.VariationAddContext):
        pass

    # Exit a parse tree produced by SMELParser#variationAdd.
    def exitVariationAdd(self, ctx:SMELParser.VariationAddContext):
        pass


    # Enter a parse tree produced by SMELParser#relTypeAdd.
    def enterRelTypeAdd(self, ctx:SMELParser.RelTypeAddContext):
        pass

    # Exit a parse tree produced by SMELParser#relTypeAdd.
    def exitRelTypeAdd(self, ctx:SMELParser.RelTypeAddContext):
        pass


    # Enter a parse tree produced by SMELParser#delete.
    def enterDelete(self, ctx:SMELParser.DeleteContext):
        pass

    # Exit a parse tree produced by SMELParser#delete.
    def exitDelete(self, ctx:SMELParser.DeleteContext):
        pass


    # Enter a parse tree produced by SMELParser#attributeDelete.
    def enterAttributeDelete(self, ctx:SMELParser.AttributeDeleteContext):
        pass

    # Exit a parse tree produced by SMELParser#attributeDelete.
    def exitAttributeDelete(self, ctx:SMELParser.AttributeDeleteContext):
        pass


    # Enter a parse tree produced by SMELParser#referenceDelete.
    def enterReferenceDelete(self, ctx:SMELParser.ReferenceDeleteContext):
        pass

    # Exit a parse tree produced by SMELParser#referenceDelete.
    def exitReferenceDelete(self, ctx:SMELParser.ReferenceDeleteContext):
        pass


    # Enter a parse tree produced by SMELParser#embeddedDelete.
    def enterEmbeddedDelete(self, ctx:SMELParser.EmbeddedDeleteContext):
        pass

    # Exit a parse tree produced by SMELParser#embeddedDelete.
    def exitEmbeddedDelete(self, ctx:SMELParser.EmbeddedDeleteContext):
        pass


    # Enter a parse tree produced by SMELParser#entityDelete.
    def enterEntityDelete(self, ctx:SMELParser.EntityDeleteContext):
        pass

    # Exit a parse tree produced by SMELParser#entityDelete.
    def exitEntityDelete(self, ctx:SMELParser.EntityDeleteContext):
        pass


    # Enter a parse tree produced by SMELParser#drop.
    def enterDrop(self, ctx:SMELParser.DropContext):
        pass

    # Exit a parse tree produced by SMELParser#drop.
    def exitDrop(self, ctx:SMELParser.DropContext):
        pass


    # Enter a parse tree produced by SMELParser#keyDrop.
    def enterKeyDrop(self, ctx:SMELParser.KeyDropContext):
        pass

    # Exit a parse tree produced by SMELParser#keyDrop.
    def exitKeyDrop(self, ctx:SMELParser.KeyDropContext):
        pass


    # Enter a parse tree produced by SMELParser#variationDrop.
    def enterVariationDrop(self, ctx:SMELParser.VariationDropContext):
        pass

    # Exit a parse tree produced by SMELParser#variationDrop.
    def exitVariationDrop(self, ctx:SMELParser.VariationDropContext):
        pass


    # Enter a parse tree produced by SMELParser#relTypeDrop.
    def enterRelTypeDrop(self, ctx:SMELParser.RelTypeDropContext):
        pass

    # Exit a parse tree produced by SMELParser#relTypeDrop.
    def exitRelTypeDrop(self, ctx:SMELParser.RelTypeDropContext):
        pass


    # Enter a parse tree produced by SMELParser#rename.
    def enterRename(self, ctx:SMELParser.RenameContext):
        pass

    # Exit a parse tree produced by SMELParser#rename.
    def exitRename(self, ctx:SMELParser.RenameContext):
        pass


    # Enter a parse tree produced by SMELParser#featureRename.
    def enterFeatureRename(self, ctx:SMELParser.FeatureRenameContext):
        pass

    # Exit a parse tree produced by SMELParser#featureRename.
    def exitFeatureRename(self, ctx:SMELParser.FeatureRenameContext):
        pass


    # Enter a parse tree produced by SMELParser#entityRename.
    def enterEntityRename(self, ctx:SMELParser.EntityRenameContext):
        pass

    # Exit a parse tree produced by SMELParser#entityRename.
    def exitEntityRename(self, ctx:SMELParser.EntityRenameContext):
        pass


    # Enter a parse tree produced by SMELParser#relTypeRename.
    def enterRelTypeRename(self, ctx:SMELParser.RelTypeRenameContext):
        pass

    # Exit a parse tree produced by SMELParser#relTypeRename.
    def exitRelTypeRename(self, ctx:SMELParser.RelTypeRenameContext):
        pass


    # Enter a parse tree produced by SMELParser#keyType.
    def enterKeyType(self, ctx:SMELParser.KeyTypeContext):
        pass

    # Exit a parse tree produced by SMELParser#keyType.
    def exitKeyType(self, ctx:SMELParser.KeyTypeContext):
        pass


    # Enter a parse tree produced by SMELParser#keyClause.
    def enterKeyClause(self, ctx:SMELParser.KeyClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#keyClause.
    def exitKeyClause(self, ctx:SMELParser.KeyClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#referencesClause.
    def enterReferencesClause(self, ctx:SMELParser.ReferencesClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#referencesClause.
    def exitReferencesClause(self, ctx:SMELParser.ReferencesClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withColumnsClause.
    def enterWithColumnsClause(self, ctx:SMELParser.WithColumnsClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withColumnsClause.
    def exitWithColumnsClause(self, ctx:SMELParser.WithColumnsClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#identifierList.
    def enterIdentifierList(self, ctx:SMELParser.IdentifierListContext):
        pass

    # Exit a parse tree produced by SMELParser#identifierList.
    def exitIdentifierList(self, ctx:SMELParser.IdentifierListContext):
        pass


    # Enter a parse tree produced by SMELParser#variationClause.
    def enterVariationClause(self, ctx:SMELParser.VariationClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#variationClause.
    def exitVariationClause(self, ctx:SMELParser.VariationClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withAttributesClause.
    def enterWithAttributesClause(self, ctx:SMELParser.WithAttributesClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withAttributesClause.
    def exitWithAttributesClause(self, ctx:SMELParser.WithAttributesClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withRelationshipsClause.
    def enterWithRelationshipsClause(self, ctx:SMELParser.WithRelationshipsClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withRelationshipsClause.
    def exitWithRelationshipsClause(self, ctx:SMELParser.WithRelationshipsClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withCountClause.
    def enterWithCountClause(self, ctx:SMELParser.WithCountClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withCountClause.
    def exitWithCountClause(self, ctx:SMELParser.WithCountClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#relTypeClause.
    def enterRelTypeClause(self, ctx:SMELParser.RelTypeClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#relTypeClause.
    def exitRelTypeClause(self, ctx:SMELParser.RelTypeClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#withPropertiesClause.
    def enterWithPropertiesClause(self, ctx:SMELParser.WithPropertiesClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#withPropertiesClause.
    def exitWithPropertiesClause(self, ctx:SMELParser.WithPropertiesClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#extract.
    def enterExtract(self, ctx:SMELParser.ExtractContext):
        pass

    # Exit a parse tree produced by SMELParser#extract.
    def exitExtract(self, ctx:SMELParser.ExtractContext):
        pass


    # Enter a parse tree produced by SMELParser#extractClause.
    def enterExtractClause(self, ctx:SMELParser.ExtractClauseContext):
        pass

    # Exit a parse tree produced by SMELParser#extractClause.
    def exitExtractClause(self, ctx:SMELParser.ExtractClauseContext):
        pass


    # Enter a parse tree produced by SMELParser#cardinalityType.
    def enterCardinalityType(self, ctx:SMELParser.CardinalityTypeContext):
        pass

    # Exit a parse tree produced by SMELParser#cardinalityType.
    def exitCardinalityType(self, ctx:SMELParser.CardinalityTypeContext):
        pass


    # Enter a parse tree produced by SMELParser#dataType.
    def enterDataType(self, ctx:SMELParser.DataTypeContext):
        pass

    # Exit a parse tree produced by SMELParser#dataType.
    def exitDataType(self, ctx:SMELParser.DataTypeContext):
        pass


    # Enter a parse tree produced by SMELParser#qualifiedName.
    def enterQualifiedName(self, ctx:SMELParser.QualifiedNameContext):
        pass

    # Exit a parse tree produced by SMELParser#qualifiedName.
    def exitQualifiedName(self, ctx:SMELParser.QualifiedNameContext):
        pass


    # Enter a parse tree produced by SMELParser#pathSegment.
    def enterPathSegment(self, ctx:SMELParser.PathSegmentContext):
        pass

    # Exit a parse tree produced by SMELParser#pathSegment.
    def exitPathSegment(self, ctx:SMELParser.PathSegmentContext):
        pass


    # Enter a parse tree produced by SMELParser#identifier.
    def enterIdentifier(self, ctx:SMELParser.IdentifierContext):
        pass

    # Exit a parse tree produced by SMELParser#identifier.
    def exitIdentifier(self, ctx:SMELParser.IdentifierContext):
        pass


    # Enter a parse tree produced by SMELParser#condition.
    def enterCondition(self, ctx:SMELParser.ConditionContext):
        pass

    # Exit a parse tree produced by SMELParser#condition.
    def exitCondition(self, ctx:SMELParser.ConditionContext):
        pass


    # Enter a parse tree produced by SMELParser#literal.
    def enterLiteral(self, ctx:SMELParser.LiteralContext):
        pass

    # Exit a parse tree produced by SMELParser#literal.
    def exitLiteral(self, ctx:SMELParser.LiteralContext):
        pass



del SMELParser