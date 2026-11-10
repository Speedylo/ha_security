# 14. Learning Strategies

This project asked me to work in areas I had not studied before, among them the isolation features of the Linux kernel, the internals of the Python interpreter and the design of a security evaluation. This section describes the three strategies I used to learn them.

## 14.1 Learning from primary sources

I learned most from reading the closest prior work in full rather than in summary. Corno and Mannella (2022) showed that an integration can walk the Python garbage collector to reach another integration's live objects, and that single result ruled out every design that enforces permissions inside the platform's own process, before I had written any code. Read less carefully, the paper would have pointed to the obvious first design, a permission check wrapped around the platform's core object, which would have failed in a way no test written for it would reveal. For the kernel, I worked from the manual pages of each interface the framework uses (Linux man-pages project, n.d.-b, n.d.-d), because the limits that matter for security are stated there.

## 14.2 Learning by predicting

Before each experiment I wrote down the result I expected and committed it, so that the measurement could show me wrong. Many of my early predictions were wrong, and those taught me the most. I expected the integrations drawn at random from the catalogue to load less often than the most-installed ones, because less popular code is usually less well maintained, but they loaded more often, 92% against 84% (Section 12.2). Had I not written the expectation down first, I would not have noticed that it had failed, nor looked for the reason: a typical integration needs less from the platform, so it has less that can go missing.

## 14.3 Owning code written with AI assistance

Much of the code was written with AI assistance (Section 13), so I could not assume that I understood every mechanism in it. To close that gap, I followed a learning curriculum covering each mechanism the framework relies on, from how the kernel represents a process to namespaces, system-call filtering and resource limits. For each topic I used the official documentation, book chapters and video lectures on YouTube. The aim was to be able to explain and defend each mechanism myself, rather than only to recognise it in the project's code.
