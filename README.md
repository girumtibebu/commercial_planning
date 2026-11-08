# Commercial Planning

A cost planning workspace for Frappe and ERPNext. It connects the price you quote a client to the cost you plan to spend, from the first quotation to the finished project.

The client-facing quotation and your internal costs are different. A quotation item such as "LED Screen Package" may be built from a vendor package, transport and technicians. This app keeps both views and links them.

## What it does

- **One plan per job.** The plan follows a Quotation, then the Sales Order, then the Project.
- **Cost tree.** Each quotation item becomes a category. Under it you add cost lines. A category total is the sum of its lines.
- **Versions.** Every stage of the plan is a version: Quotation, Sales Order, Project Budget, Forecast, or any version you add. A version can be copied, frozen, approved, and compared with others. Old versions are never overwritten.
- **Stays in step with the document.** If a quotation item is added, or its quantity, unit or price changes, the plan tells you. You decide when to refresh it.
- **Automatic versions.** Creating a Sales Order or a Project adds the next version. The version it came from is frozen. An amended quotation gets a new version.
- **Review.** Activity feed, comments, assignments, tags, sharing and attachments, like the standard form.
- **Roles.** Commercial Planner, Commercial Management, and the ERPNext Projects Manager role.

## Install

Requires Frappe and ERPNext, version 16.

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/girumtibebu/commercial_planning --branch main
bench --site your.site install-app commercial_planning
```

The built interface is included in the repository. You do not need to run `yarn build` to use it.

## Use

Open a Quotation, Sales Order or Project and click **Commercial Planning**. The workspace opens in a new tab at `/commercial-planning`.

## Develop

The interface is a Vue 3 app with Frappe UI, in `frontend/`.

```bash
cd apps/commercial_planning/frontend
yarn install
yarn build
```

The build writes to `commercial_planning/public/frontend` and `commercial_planning/www/commercial-planning.html`.

Run the tests on a development site:

```bash
bench --site your.site set-config allow_tests true
bench --site your.site run-tests --app commercial_planning
```

The backend code is in `commercial_planning/services` (rules) and `commercial_planning/api` (whitelisted methods).

## License

MIT
