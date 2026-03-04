# Generated from grammar/SMEL_Pauschalisiert.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SMEL_PauschalisiertParser import SMEL_PauschalisiertParser
else:
    from SMEL_PauschalisiertParser import SMEL_PauschalisiertParser

# This class defines a complete listener for a parse tree produced by SMEL_PauschalisiertParser.
class SMEL_PauschalisiertListener(ParseTreeListener):

    # Enter a parse tree produced by SMEL_PauschalisiertParser#migration.
    def enterMigration(self, ctx:SMEL_PauschalisiertParser.MigrationContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#migration.
    def exitMigration(self, ctx:SMEL_PauschalisiertParser.MigrationContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#header.
    def enterHeader(self, ctx:SMEL_PauschalisiertParser.HeaderContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#header.
    def exitHeader(self, ctx:SMEL_PauschalisiertParser.HeaderContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#migrationDecl.
    def enterMigrationDecl(self, ctx:SMEL_PauschalisiertParser.MigrationDeclContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#migrationDecl.
    def exitMigrationDecl(self, ctx:SMEL_PauschalisiertParser.MigrationDeclContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#fromToDecl.
    def enterFromToDecl(self, ctx:SMEL_PauschalisiertParser.FromToDeclContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#fromToDecl.
    def exitFromToDecl(self, ctx:SMEL_PauschalisiertParser.FromToDeclContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#usingDecl.
    def enterUsingDecl(self, ctx:SMEL_PauschalisiertParser.UsingDeclContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#usingDecl.
    def exitUsingDecl(self, ctx:SMEL_PauschalisiertParser.UsingDeclContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#databaseType.
    def enterDatabaseType(self, ctx:SMEL_PauschalisiertParser.DatabaseTypeContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#databaseType.
    def exitDatabaseType(self, ctx:SMEL_PauschalisiertParser.DatabaseTypeContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#version.
    def enterVersion(self, ctx:SMEL_PauschalisiertParser.VersionContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#version.
    def exitVersion(self, ctx:SMEL_PauschalisiertParser.VersionContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#operation.
    def enterOperation(self, ctx:SMEL_PauschalisiertParser.OperationContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#operation.
    def exitOperation(self, ctx:SMEL_PauschalisiertParser.OperationContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#add_ps.
    def enterAdd_ps(self, ctx:SMEL_PauschalisiertParser.Add_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#add_ps.
    def exitAdd_ps(self, ctx:SMEL_PauschalisiertParser.Add_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeAdd.
    def enterAttributeAdd(self, ctx:SMEL_PauschalisiertParser.AttributeAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeAdd.
    def exitAttributeAdd(self, ctx:SMEL_PauschalisiertParser.AttributeAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeClause.
    def enterAttributeClause(self, ctx:SMEL_PauschalisiertParser.AttributeClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeClause.
    def exitAttributeClause(self, ctx:SMEL_PauschalisiertParser.AttributeClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withTypeClause.
    def enterWithTypeClause(self, ctx:SMEL_PauschalisiertParser.WithTypeClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withTypeClause.
    def exitWithTypeClause(self, ctx:SMEL_PauschalisiertParser.WithTypeClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withDefaultClause.
    def enterWithDefaultClause(self, ctx:SMEL_PauschalisiertParser.WithDefaultClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withDefaultClause.
    def exitWithDefaultClause(self, ctx:SMEL_PauschalisiertParser.WithDefaultClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#notNullClause.
    def enterNotNullClause(self, ctx:SMEL_PauschalisiertParser.NotNullClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#notNullClause.
    def exitNotNullClause(self, ctx:SMEL_PauschalisiertParser.NotNullClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#constraintAdd.
    def enterConstraintAdd(self, ctx:SMEL_PauschalisiertParser.ConstraintAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#constraintAdd.
    def exitConstraintAdd(self, ctx:SMEL_PauschalisiertParser.ConstraintAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#constraintClause.
    def enterConstraintClause(self, ctx:SMEL_PauschalisiertParser.ConstraintClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#constraintClause.
    def exitConstraintClause(self, ctx:SMEL_PauschalisiertParser.ConstraintClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#embeddedAdd.
    def enterEmbeddedAdd(self, ctx:SMEL_PauschalisiertParser.EmbeddedAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#embeddedAdd.
    def exitEmbeddedAdd(self, ctx:SMEL_PauschalisiertParser.EmbeddedAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#embeddedClause.
    def enterEmbeddedClause(self, ctx:SMEL_PauschalisiertParser.EmbeddedClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#embeddedClause.
    def exitEmbeddedClause(self, ctx:SMEL_PauschalisiertParser.EmbeddedClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withStructureClause.
    def enterWithStructureClause(self, ctx:SMEL_PauschalisiertParser.WithStructureClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withStructureClause.
    def exitWithStructureClause(self, ctx:SMEL_PauschalisiertParser.WithStructureClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#entityAdd.
    def enterEntityAdd(self, ctx:SMEL_PauschalisiertParser.EntityAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#entityAdd.
    def exitEntityAdd(self, ctx:SMEL_PauschalisiertParser.EntityAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#entityClause.
    def enterEntityClause(self, ctx:SMEL_PauschalisiertParser.EntityClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#entityClause.
    def exitEntityClause(self, ctx:SMEL_PauschalisiertParser.EntityClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withKeyClause.
    def enterWithKeyClause(self, ctx:SMEL_PauschalisiertParser.WithKeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withKeyClause.
    def exitWithKeyClause(self, ctx:SMEL_PauschalisiertParser.WithKeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#keyAdd.
    def enterKeyAdd(self, ctx:SMEL_PauschalisiertParser.KeyAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#keyAdd.
    def exitKeyAdd(self, ctx:SMEL_PauschalisiertParser.KeyAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#keyColumns.
    def enterKeyColumns(self, ctx:SMEL_PauschalisiertParser.KeyColumnsContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#keyColumns.
    def exitKeyColumns(self, ctx:SMEL_PauschalisiertParser.KeyColumnsContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#labelAdd.
    def enterLabelAdd(self, ctx:SMEL_PauschalisiertParser.LabelAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#labelAdd.
    def exitLabelAdd(self, ctx:SMEL_PauschalisiertParser.LabelAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#reltypeAdd.
    def enterReltypeAdd(self, ctx:SMEL_PauschalisiertParser.ReltypeAddContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#reltypeAdd.
    def exitReltypeAdd(self, ctx:SMEL_PauschalisiertParser.ReltypeAddContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#delete_ps.
    def enterDelete_ps(self, ctx:SMEL_PauschalisiertParser.Delete_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#delete_ps.
    def exitDelete_ps(self, ctx:SMEL_PauschalisiertParser.Delete_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeDelete.
    def enterAttributeDelete(self, ctx:SMEL_PauschalisiertParser.AttributeDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeDelete.
    def exitAttributeDelete(self, ctx:SMEL_PauschalisiertParser.AttributeDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#constraintDelete.
    def enterConstraintDelete(self, ctx:SMEL_PauschalisiertParser.ConstraintDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#constraintDelete.
    def exitConstraintDelete(self, ctx:SMEL_PauschalisiertParser.ConstraintDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#embeddedDelete.
    def enterEmbeddedDelete(self, ctx:SMEL_PauschalisiertParser.EmbeddedDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#embeddedDelete.
    def exitEmbeddedDelete(self, ctx:SMEL_PauschalisiertParser.EmbeddedDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#entityDelete.
    def enterEntityDelete(self, ctx:SMEL_PauschalisiertParser.EntityDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#entityDelete.
    def exitEntityDelete(self, ctx:SMEL_PauschalisiertParser.EntityDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#keyDelete.
    def enterKeyDelete(self, ctx:SMEL_PauschalisiertParser.KeyDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#keyDelete.
    def exitKeyDelete(self, ctx:SMEL_PauschalisiertParser.KeyDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#labelDelete.
    def enterLabelDelete(self, ctx:SMEL_PauschalisiertParser.LabelDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#labelDelete.
    def exitLabelDelete(self, ctx:SMEL_PauschalisiertParser.LabelDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#reltypeDelete.
    def enterReltypeDelete(self, ctx:SMEL_PauschalisiertParser.ReltypeDeleteContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#reltypeDelete.
    def exitReltypeDelete(self, ctx:SMEL_PauschalisiertParser.ReltypeDeleteContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#remove_ps.
    def enterRemove_ps(self, ctx:SMEL_PauschalisiertParser.Remove_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#remove_ps.
    def exitRemove_ps(self, ctx:SMEL_PauschalisiertParser.Remove_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#uniqueKeyRemove.
    def enterUniqueKeyRemove(self, ctx:SMEL_PauschalisiertParser.UniqueKeyRemoveContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#uniqueKeyRemove.
    def exitUniqueKeyRemove(self, ctx:SMEL_PauschalisiertParser.UniqueKeyRemoveContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#foreignKeyRemove.
    def enterForeignKeyRemove(self, ctx:SMEL_PauschalisiertParser.ForeignKeyRemoveContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#foreignKeyRemove.
    def exitForeignKeyRemove(self, ctx:SMEL_PauschalisiertParser.ForeignKeyRemoveContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#labelRemove.
    def enterLabelRemove(self, ctx:SMEL_PauschalisiertParser.LabelRemoveContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#labelRemove.
    def exitLabelRemove(self, ctx:SMEL_PauschalisiertParser.LabelRemoveContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#rename_ps.
    def enterRename_ps(self, ctx:SMEL_PauschalisiertParser.Rename_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#rename_ps.
    def exitRename_ps(self, ctx:SMEL_PauschalisiertParser.Rename_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeRename.
    def enterAttributeRename(self, ctx:SMEL_PauschalisiertParser.AttributeRenameContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeRename.
    def exitAttributeRename(self, ctx:SMEL_PauschalisiertParser.AttributeRenameContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#entityRename.
    def enterEntityRename(self, ctx:SMEL_PauschalisiertParser.EntityRenameContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#entityRename.
    def exitEntityRename(self, ctx:SMEL_PauschalisiertParser.EntityRenameContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#reltypeRename.
    def enterReltypeRename(self, ctx:SMEL_PauschalisiertParser.ReltypeRenameContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#reltypeRename.
    def exitReltypeRename(self, ctx:SMEL_PauschalisiertParser.ReltypeRenameContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#keyType.
    def enterKeyType(self, ctx:SMEL_PauschalisiertParser.KeyTypeContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#keyType.
    def exitKeyType(self, ctx:SMEL_PauschalisiertParser.KeyTypeContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#keyClause.
    def enterKeyClause(self, ctx:SMEL_PauschalisiertParser.KeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#keyClause.
    def exitKeyClause(self, ctx:SMEL_PauschalisiertParser.KeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#referencesClause.
    def enterReferencesClause(self, ctx:SMEL_PauschalisiertParser.ReferencesClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#referencesClause.
    def exitReferencesClause(self, ctx:SMEL_PauschalisiertParser.ReferencesClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withColumnsClause.
    def enterWithColumnsClause(self, ctx:SMEL_PauschalisiertParser.WithColumnsClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withColumnsClause.
    def exitWithColumnsClause(self, ctx:SMEL_PauschalisiertParser.WithColumnsClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#identifierList.
    def enterIdentifierList(self, ctx:SMEL_PauschalisiertParser.IdentifierListContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#identifierList.
    def exitIdentifierList(self, ctx:SMEL_PauschalisiertParser.IdentifierListContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#flatten_ps.
    def enterFlatten_ps(self, ctx:SMEL_PauschalisiertParser.Flatten_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#flatten_ps.
    def exitFlatten_ps(self, ctx:SMEL_PauschalisiertParser.Flatten_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unflatten_ps.
    def enterUnflatten_ps(self, ctx:SMEL_PauschalisiertParser.Unflatten_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unflatten_ps.
    def exitUnflatten_ps(self, ctx:SMEL_PauschalisiertParser.Unflatten_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unnest_ps.
    def enterUnnest_ps(self, ctx:SMEL_PauschalisiertParser.Unnest_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unnest_ps.
    def exitUnnest_ps(self, ctx:SMEL_PauschalisiertParser.Unnest_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unnestCarryList.
    def enterUnnestCarryList(self, ctx:SMEL_PauschalisiertParser.UnnestCarryListContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unnestCarryList.
    def exitUnnestCarryList(self, ctx:SMEL_PauschalisiertParser.UnnestCarryListContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unnestCarryField.
    def enterUnnestCarryField(self, ctx:SMEL_PauschalisiertParser.UnnestCarryFieldContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unnestCarryField.
    def exitUnnestCarryField(self, ctx:SMEL_PauschalisiertParser.UnnestCarryFieldContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unnestFieldList.
    def enterUnnestFieldList(self, ctx:SMEL_PauschalisiertParser.UnnestFieldListContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unnestFieldList.
    def exitUnnestFieldList(self, ctx:SMEL_PauschalisiertParser.UnnestFieldListContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#AttributeField.
    def enterAttributeField(self, ctx:SMEL_PauschalisiertParser.AttributeFieldContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#AttributeField.
    def exitAttributeField(self, ctx:SMEL_PauschalisiertParser.AttributeFieldContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#NestedField.
    def enterNestedField(self, ctx:SMEL_PauschalisiertParser.NestedFieldContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#NestedField.
    def exitNestedField(self, ctx:SMEL_PauschalisiertParser.NestedFieldContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#unwind_ps.
    def enterUnwind_ps(self, ctx:SMEL_PauschalisiertParser.Unwind_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#unwind_ps.
    def exitUnwind_ps(self, ctx:SMEL_PauschalisiertParser.Unwind_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#wind_ps.
    def enterWind_ps(self, ctx:SMEL_PauschalisiertParser.Wind_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#wind_ps.
    def exitWind_ps(self, ctx:SMEL_PauschalisiertParser.Wind_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#nest_ps.
    def enterNest_ps(self, ctx:SMEL_PauschalisiertParser.Nest_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#nest_ps.
    def exitNest_ps(self, ctx:SMEL_PauschalisiertParser.Nest_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#copy_ps.
    def enterCopy_ps(self, ctx:SMEL_PauschalisiertParser.Copy_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#copy_ps.
    def exitCopy_ps(self, ctx:SMEL_PauschalisiertParser.Copy_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeCopy.
    def enterAttributeCopy(self, ctx:SMEL_PauschalisiertParser.AttributeCopyContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeCopy.
    def exitAttributeCopy(self, ctx:SMEL_PauschalisiertParser.AttributeCopyContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#entityCopy.
    def enterEntityCopy(self, ctx:SMEL_PauschalisiertParser.EntityCopyContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#entityCopy.
    def exitEntityCopy(self, ctx:SMEL_PauschalisiertParser.EntityCopyContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#move_ps.
    def enterMove_ps(self, ctx:SMEL_PauschalisiertParser.Move_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#move_ps.
    def exitMove_ps(self, ctx:SMEL_PauschalisiertParser.Move_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#merge_ps.
    def enterMerge_ps(self, ctx:SMEL_PauschalisiertParser.Merge_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#merge_ps.
    def exitMerge_ps(self, ctx:SMEL_PauschalisiertParser.Merge_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#split_ps.
    def enterSplit_ps(self, ctx:SMEL_PauschalisiertParser.Split_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#split_ps.
    def exitSplit_ps(self, ctx:SMEL_PauschalisiertParser.Split_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#splitPartPs.
    def enterSplitPartPs(self, ctx:SMEL_PauschalisiertParser.SplitPartPsContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#splitPartPs.
    def exitSplitPartPs(self, ctx:SMEL_PauschalisiertParser.SplitPartPsContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#cast_ps.
    def enterCast_ps(self, ctx:SMEL_PauschalisiertParser.Cast_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#cast_ps.
    def exitCast_ps(self, ctx:SMEL_PauschalisiertParser.Cast_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#attributeCast.
    def enterAttributeCast(self, ctx:SMEL_PauschalisiertParser.AttributeCastContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#attributeCast.
    def exitAttributeCast(self, ctx:SMEL_PauschalisiertParser.AttributeCastContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#constraintCast.
    def enterConstraintCast(self, ctx:SMEL_PauschalisiertParser.ConstraintCastContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#constraintCast.
    def exitConstraintCast(self, ctx:SMEL_PauschalisiertParser.ConstraintCastContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#recard_ps.
    def enterRecard_ps(self, ctx:SMEL_PauschalisiertParser.Recard_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#recard_ps.
    def exitRecard_ps(self, ctx:SMEL_PauschalisiertParser.Recard_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#transform_ps.
    def enterTransform_ps(self, ctx:SMEL_PauschalisiertParser.Transform_psContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#transform_ps.
    def exitTransform_ps(self, ctx:SMEL_PauschalisiertParser.Transform_psContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#TransformToRelationship.
    def enterTransformToRelationship(self, ctx:SMEL_PauschalisiertParser.TransformToRelationshipContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#TransformToRelationship.
    def exitTransformToRelationship(self, ctx:SMEL_PauschalisiertParser.TransformToRelationshipContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#TransformToEntity.
    def enterTransformToEntity(self, ctx:SMEL_PauschalisiertParser.TransformToEntityContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#TransformToEntity.
    def exitTransformToEntity(self, ctx:SMEL_PauschalisiertParser.TransformToEntityContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withCardinalityClause.
    def enterWithCardinalityClause(self, ctx:SMEL_PauschalisiertParser.WithCardinalityClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withCardinalityClause.
    def exitWithCardinalityClause(self, ctx:SMEL_PauschalisiertParser.WithCardinalityClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#usingKeyClause.
    def enterUsingKeyClause(self, ctx:SMEL_PauschalisiertParser.UsingKeyClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#usingKeyClause.
    def exitUsingKeyClause(self, ctx:SMEL_PauschalisiertParser.UsingKeyClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#whereClause.
    def enterWhereClause(self, ctx:SMEL_PauschalisiertParser.WhereClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#whereClause.
    def exitWhereClause(self, ctx:SMEL_PauschalisiertParser.WhereClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#withAttributesClause.
    def enterWithAttributesClause(self, ctx:SMEL_PauschalisiertParser.WithAttributesClauseContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#withAttributesClause.
    def exitWithAttributesClause(self, ctx:SMEL_PauschalisiertParser.WithAttributesClauseContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#cardinalityType.
    def enterCardinalityType(self, ctx:SMEL_PauschalisiertParser.CardinalityTypeContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#cardinalityType.
    def exitCardinalityType(self, ctx:SMEL_PauschalisiertParser.CardinalityTypeContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#constraintKeyType.
    def enterConstraintKeyType(self, ctx:SMEL_PauschalisiertParser.ConstraintKeyTypeContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#constraintKeyType.
    def exitConstraintKeyType(self, ctx:SMEL_PauschalisiertParser.ConstraintKeyTypeContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#dataType.
    def enterDataType(self, ctx:SMEL_PauschalisiertParser.DataTypeContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#dataType.
    def exitDataType(self, ctx:SMEL_PauschalisiertParser.DataTypeContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#qualifiedName.
    def enterQualifiedName(self, ctx:SMEL_PauschalisiertParser.QualifiedNameContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#qualifiedName.
    def exitQualifiedName(self, ctx:SMEL_PauschalisiertParser.QualifiedNameContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#pathSegment.
    def enterPathSegment(self, ctx:SMEL_PauschalisiertParser.PathSegmentContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#pathSegment.
    def exitPathSegment(self, ctx:SMEL_PauschalisiertParser.PathSegmentContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#identifier.
    def enterIdentifier(self, ctx:SMEL_PauschalisiertParser.IdentifierContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#identifier.
    def exitIdentifier(self, ctx:SMEL_PauschalisiertParser.IdentifierContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#condition.
    def enterCondition(self, ctx:SMEL_PauschalisiertParser.ConditionContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#condition.
    def exitCondition(self, ctx:SMEL_PauschalisiertParser.ConditionContext):
        pass


    # Enter a parse tree produced by SMEL_PauschalisiertParser#literal.
    def enterLiteral(self, ctx:SMEL_PauschalisiertParser.LiteralContext):
        pass

    # Exit a parse tree produced by SMEL_PauschalisiertParser#literal.
    def exitLiteral(self, ctx:SMEL_PauschalisiertParser.LiteralContext):
        pass



del SMEL_PauschalisiertParser