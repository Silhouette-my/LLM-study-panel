declare const validators: Record<string, ((data:unknown)=>boolean)&{errors?:unknown[]}>;
export = validators;
