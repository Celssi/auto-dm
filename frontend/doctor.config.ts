export default {
  ignore: {
    overrides: [
      {
        files: ['src/games/dnd5e/character-sheet/characterSheetPdf*.tsx'],
        rules: ['react-doctor/no-tiny-text'],
      },
    ],
  },
};
