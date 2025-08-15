/* eslint-disable n/no-extraneous-import */
import js from '@eslint/js'
// eslint-disable-next-line n/no-unpublished-import
import nodePlugin from 'eslint-plugin-n'
// eslint-disable-next-line n/no-unpublished-import
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended'
// eslint-disable-next-line n/no-unpublished-import
import tseslint from 'typescript-eslint'

export default tseslint.config(
	{
		ignores: ['**/dist', '**/node_modules'],
	},
	js.configs.recommended,
	tseslint.configs.eslintRecommended,
	...tseslint.configs.recommended,
	nodePlugin.configs['flat/recommended'],
	eslintPluginPrettierRecommended,
	{
		files: ['**/*.ts'],
		languageOptions: {
			parserOptions: {
				project: true,
				tsconfigRootDir: import.meta.dirname,
			},
		},
		rules: {
			'@typescript-eslint/no-explicit-any': 'off',
			'@typescript-eslint/interface-name-prefix': 'off',
			'@typescript-eslint/no-unused-vars': [
				'error',
				{
					argsIgnorePattern: '^_',
				},
			],
			'@typescript-eslint/no-floating-promises': 'error',
		},
	},
	{
		rules: {
			curly: 'error',
			'prettier/prettier': 'error',
			'no-extra-semi': 'off',
			'n/no-unsupported-features/es-syntax': [
				'error',
				{
					ignores: ['modules'],
				},
			],
			'no-use-before-define': 'off',
			'no-warning-comments': [
				'error',
				{
					terms: ['nocommit', '@nocommit', '@no-commit'],
				},
			],
			'no-unused-vars': 'off',
			'n/no-missing-import': 'off',
		},
	},
)
