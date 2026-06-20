export default {
  ignore: {
    overrides: [
      {
        files: ['src/components/character-sheet/characterSheetPdf*.tsx'],
        rules: ['react-doctor/no-tiny-text'],
      },
    ],
  },
};
