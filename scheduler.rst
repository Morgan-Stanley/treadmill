Scheduler
=========


Overview
--------

The Treadmill scheduler is responsible for finding application placement on the
Treadmill cell. Given the collection of servers and their attributes, such as
available capacity and other constraints, Treadmill scheduler will place
applications to satisfy application demands as described in its Treadmill
manifest.

Treadmill scheduler has the following high level features:

 * It brokers placement decisions between independent users. Treadmill
   scheduler is multi-tenant, and different users do not coordinate their
   application demand.
 * Supports capacity reservations and opportunistic (non-reserved) placement.
 * Server presence aware, will reschedule applications if the server goes down.
 * Server topology aware, can spread or stack applications across different
   servers, racks and pods.
 * Supports placement constraints, reboot aware.


.. _section-paritions:

Partitions
----------

Treadmill scheduler operates on a cell. The cell is collection of servers.
Servers in the cell are divided into partitions, which are non-overlapping
subsets of servers in the cell. Servers within a partition do not need to be
homogenous, but they are considered interchangeable with regard to placement.

The number of servers in partition can vary from single digits to thousands.

When users submit applications to run on a Treadmill cell, they specify the
target partition. Partitions form a unit of administration. They can have
different SLA (alert thresholds, reboot schedules, amount of capacity available
for reservations) or be comprised from servers that have external attributes
that are not expressed in the Treadmill manifest (such as a set of firewall
rules, connectivity so downstream resources, very particular hardware, etc.).
They also can be restricted for subset of users.

On that note, while there is no limitation on number of partitions, dividing
cell into many partitions, each for a different user, is a Treadmill admin
anti-pattern. Treadmill is designed to broker capacity within a given partition
between different independent tenants, so you want to maximize the capacity
pool the scheduler is working with and not divvy it up into many small
partitions.

The general rule of thumb is that, unless you have one of the specific needs
detailed above to segregate into pools of capacity, you should avoid creating
partitions.


.. _section-multi-tenancy:

Multi-tenancy
-------------

The key features of Treadmill scheduler is multi-tenant support. Independent
users submit their applications to run on the Treadmill cell, and the job of
the scheduler is to find capacity that matches application demand, and possibly
evict applications that are lower priority than others.

In order to decide which application has higher priority, Treadmill scheduler
orders all application (per-partition) into a list. The list is ordered by
"utilization", which is a heuristic that takes into account the capacity
reserved by a given tenant, accumulated capacity demand, and other factors. The
exact details of application ordering will be described in detail later in the
document.

Once the application queue is constructed, Treadmill scheduler will try and
find suitable placement for each application, such that application demand and
other constraints are satisfied. The placement is "online", once the placement
is found, it is not revisited within the given scheduling cycle. Applications
on the left of the queue has strict priority over application on the right of
the queue. If a placement cannot be found, the scheduler will try to find
capacity by evicting applications from the right end of the queue. For those
applications that were evicted the scheduler will try to restore the placement
or find new one. If this is not possible, application will be evicted, yet it
will be left on the placement queue in pending state.

Once the queue evaluation is done, the scheduler will publish final placement
and wait for new events.


.. _section-utilization:

Tenants, allocations, and application utilization
-------------------------------------------------

Treadmill scheduler supports multi tenancy by assigning to each tenant one or
more allocations. Administratively, allocations are protected resources, and
Treadmill API will enforce access control on allocations. From scheduler
perspective the mechanics of allocation entitlements are not important.

Allocation is used to reserve capacity on a given partition.

 * Allocation has associated capacity (e.g memory, cpu, disk) and rank.
 * Each application is assigned to a single allocation. Applications within a
   given allocation form a "private allocation queue".
 * Allocation has additional property called "rank" and "rank adjustment",
   which are important when constructing global application demand queue.
 * Allocations form a hierarchy. Each allocation can have child allocations,
   with their own associated capacity, application queue and rank.

Allocation private queue is controlled by the user. Within the private
allocation queue, applications are ordered by "priority". Users have full
control over specifying application priority, and application priority can be
adjusted anytime by the application owner.

Priority allows individual users to express which applications are more
important for them. Priority values range from 100 (most important) to 0.
Priorities matter only within a given allocation.

Advanced: Priority 0 has a special meaning, see :ref:`section-priority-0`.

Within allocation, applications are ordered by priority. Next step is to
construct "utilization", which is roughly a ratio of total accumulated capacity
to reserved. As capacity is a vector (memory, cpu, disk, …) the max of the
ratio is used.

For each application in the allocation, the scheduler will maintain a tuple of
(dynamic-rank, utilization-before, utilization-after). Dynamic rank is
constructed from allocation base rank and rank adjustment attributes. If
reserved capacity is not exceeded, dynamic rank is base rank minus rank
adjustment. If reserved capacity is exceeded, dynamic rank equals to base rank.

All private allocation queue are merged, bottom up, sorted by dynamic rank and
utilization. Allocation structure is hierarchical, and rank, rank adjustment
and utilization is recalculated on each level.

Top level allocation will contain all applications in the partition, ordered by
rank and utilization.

At each level, the following invariants are maintained:

 * Applications from allocations with lower rank are first in the queue.
 * Applications within reserved capacity has rank less or equal to applications
   above reserved capacity.
 * Applications within reserved capacity has utilization < 1.

The hierarchical merge allows to achieve the following design goals:

 * Different tenants reserve capacity independently (Treadmill does not allow
   for reservations to go beyond total capacity of the cell)
 * Tenant hierarchy allows to offer unused capacity to the sibling first,
   parents later. Consider someone running grid application, and creating dev
   and prod sub allocations. If prod is underutilized, capacity will be offered
   first to the test grid, then to other Treadmill users. Similarly, stopping
   test grid will boost capacity for prod grid first (sibling).
 * Favor production applications to test (qa, uat). Typical setup is to
   configure all allocations with same base rank, but assign different
   adjustment to allocations for different environments. Prod allocations are
   configured with rank adjustment 3, uat with 2, qa with 1, dev - 0. As such,
   global queue will be partitioned as following: prod applications (ordered by
   utilization) running within reserved capacity, uat applications within
   reserved capacity, … , dev applications within reserved capacity,
   non-reserved. Such scheme ensures that in the event of catastrophic capacity
   failure production application running within reserved capacity will be
   evicted last.


.. _section-topology-constraints:

Server topology constraints
---------------------------

Servers in the cell are organized in a hierarchy that aims to reflect physical
topology of the datacenter.

Typical structure is server, rack, pod (rack is collection of servers, pod is
collection of racks).

Treadmill scheduler supports two placement strategies - stack and spread.
 * "spread" means that placements will be attempted across all siblings in the
   same level of the hierarchy, spreading instances across the level.
 * "stack" means that placements will be attempted on each siblings in the same
   level of the hierarchy, iteratively until they fill up, stacking all
   instances on the same entity of the level before going to the next.

Placement strategy can be specified in the application manifest. The default
strategy, if not specified, is "spread" (if you run two instances of a web
server for HA, you do want them as spread out between server/rack/pod as
possible).

Placement strategies can be different for different levels. For examples, one
may want to spread application across servers but stack them on rack and pod
level, for backend data locality.

In addition to placement strategies, Treadmill allows to specify affinity limit
constraints. These constraints will ensure that no more than N applications of
same affinity are placed at the same level of the hierarchy (server, rack or
pod).

Combining placement strategies with affinity limit constraints allows to
express various HA/performance scenarios for application placement.


.. _section-application-lifetime:

Application lifetime constraints and reboot awareness
-----------------------------------------------------

The Treadmill scheduler is aware of the expected lifetime (time in-between
maintenance windows) for every servers in the cell. Partition settings allow to
define a "work window", which days of the week (and at what time), during which
servers can be taken down for reboot, upgrade, rebuild, etc.

Based on a typical schedule, e.g. once in three weeks, the scheduler will set
the lifetime of each server such that the percentage of servers in the cell
undergoing maintenance during each "work window" spreads across the three weeks.

Once a server reaches the end of its expected lifetime, the maintenance script
will be kicked off.


On the application side, one can specify a desired lease time in the Treadmill
manifest which will instruct the scheduler to place the application only on
servers that have an expected lifetime greater than the requested lease time.

Furthermore, Treadmill allows the renewal of application lease time. Note that
this request may result in the relocation of the application to a server with
sufficient lifetime if the current placement doesn't satisfy the new lease
requirement.

Typical usage of application lease time is to be able to provide
some minimum SLAs for "always on" applications while the Treadmill cell itself
has a rolling maintenance schedule across its servers.
For example, by having multiple instances of an application and by using an
application supervisor to regularly renew leases, one instance at a time, we
can ensure that multiple instances of the same applications are not placed on
servers that have the same "work window" and may be going down at the same
time.


.. _section-priority-0:

Priority-0 applications
-----------------------

Setting application priority to zero instructs the scheduler to place this
application at the very end of the global queue. As such, priority zero
applications will run only when there is no capacity pressure on the cell and
will the first evicted when the scheduler is scavenging for capacity.

Applications running as priority-0 can be billed less than applications with
greater than zero priority.

Typical usage for priority-0 apps are for idle grid/worker instances that have
long warmup time. By adjusting priority of idle instances to 0, these instance
will only keep running if there is no capacity pressure on the cell.


.. _section-real-world:

Treadmill scheduler in the real world
-------------------------------------

Treadmill is used to manage cloud applications in Morgan Stanley. Treadmill is
deployed globally, with cells aligned to the data centers, each forming a
failure domain.

Size of the cells varies, from thousands servers in largest data centers to
dozens in smaller ones.

Typical setup for large cell may include small number of partitions (max
partitions count today is 3). Total number of applications on the cell counts
in thousands. Typically there will be a more applications scheduled than can be
accommodated, so it is common to see applications pending on the cell (consider
build jobs).

On each cell, Treadmill brokers capacity for hundreds of independent users.
Some users run hundreds of application instances, others may run pair of web
server apps, or single interactive app (consider Python notebook).

Treadmill reservation system, combined with rank adjustment scheme to promote
production applications first, proved to be resilient against capacity
failures.

For best results, we limit total reserved capacity to 75% of the total capacity
of the cell. Once reserved capacity reaches 75% limit, we either provision more
servers or deny reservations.

Treadmill scheduler works well if individual application demand is order of
magnitude smaller than server capacity. Consider servers with 48G of RAM,
applications demanding 40G of ram will leave a lot of unoccupied space, and
reservation promises will start to break (due to fragmentation).

We try to build cells with large servers - 128/256G RAM, 32 cores. Using large
servers ensures that reservation system will not break.

It is possible to game the scheduler by requesting demand that will fragment
the cell, or requesting constraints that are difficult to satisfy. We consider
our environment non-cooperative, yet not hostile. While the scheduler tries to
cater for various edge conditions and DoS attacks, using Treadmill scheduler in
hostile environment is not fully researched.
